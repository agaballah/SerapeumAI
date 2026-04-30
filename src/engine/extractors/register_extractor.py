import logging
import json
import uuid
import pandas as pd
from typing import List, Dict, Any

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

class ExcelRegisterExtractor(BaseExtractor):
    """
    Extracts tabular data from Excel files (Registers/Logs).
    Uses Pandas to infer headers and output strict Key-Value rows.
    """
    
    @property
    def id(self) -> str:
        return "excel-register-extractor-v1"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def supported_extensions(self) -> List[str]:
        return [".xlsx", ".xls"]

    def _detect_header_row(self, df_peek: pd.DataFrame) -> int:
        """
        Scans values in the dataframe to find the most likely header row.
        Score based on common keywords.
        """
        KEYWORDS = {
            "id", "no", "number", "code", "tag",                        # Identity
            "description", "title", "subject", "name",                  # Content
            "date", "start", "finish", "submission", "approval",        # Time
            "status", "state", "phase",                                 # Workflow
            "rev", "revision", "ver", "version",                        # Versioning
            "qty", "quantity", "unit", "amount", "cost", "price",       # Quantities
            "discipline", "trade", "area", "zone", "location"           # Attributes
        }
        
        best_score = 0
        best_idx = 0
        
        # Iterate row by row (up to 30)
        for idx, row in df_peek.iterrows():
            # Convert row values to string, lower, strip
            row_vals = [str(v).lower().strip() for v in row.values if pd.notna(v)]
            if not row_vals:
                continue
            
            score = 0
            for val in row_vals:
                # Exact match or substring match
                # e.g. "Activity ID" contains "id"
                if any(k in val for k in KEYWORDS):
                    score += 1
            
            # Penalize very long text (likely description or title block)
            avg_len = sum(len(v) for v in row_vals) / len(row_vals)
            if avg_len > 50:
                score -= 2

            if score > best_score:
                best_score = score
                best_idx = idx
        
        # Threshold: if practically no keywords found, fallback to 0
        return best_idx if best_score >= 1 else 0

    def extract(self, file_path: str, context: Dict[str, Any] = None) -> ExtractionResult:
        records = []
        diagnostics = []
        
        
        try:
            # Load all sheets once, then inspect each sheet header before full extraction.
            # Diagnostics are kept in-memory and through logger only; no debug file is written.
            xls = pd.read_excel(file_path, sheet_name=None, dtype=str)
            diagnostics.append(f"Sheets found: {list(xls.keys())}")
            logger.debug("Excel register sheets found in %s: %s", file_path, list(xls.keys()))

            for sheet_name in xls.keys():
                # Read first 30 rows to sniff header.
                df_peek = pd.read_excel(file_path, sheet_name=sheet_name, nrows=30, header=None, dtype=str)
                header_row_idx = self._detect_header_row(df_peek)
                diagnostics.append(f"Sheet {sheet_name}: detected header row {header_row_idx}")
                logger.debug("Excel register sheet %s detected header row %s", sheet_name, header_row_idx)

                start_row = header_row_idx if header_row_idx is not None else 0
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=start_row, dtype=str)

                if header_row_idx is None and len(df) < 2:
                    diagnostics.append(f"Sheet {sheet_name}: empty or unstructured, skipped")
                    continue

                # Clean keys.
                df.columns = [str(c).strip() for c in df.columns]

                # Iterate rows.
                for idx, row in df.iterrows():
                    row_data = {
                        k: v
                        for k, v in row.to_dict().items()
                        if pd.notna(v) and str(v) != "nan" and v != ""
                    }

                    if not row_data:
                        continue

                    records.append({
                        "type": "register_row",
                        "data": {
                            "sheet_name": sheet_name,
                            "row_index": idx + start_row + 1,
                            "content": row_data
                        },
                        "provenance": {"sheet": sheet_name, "row": idx + start_row + 1}
                    })

            diagnostics.append(f"Total register rows extracted: {len(records)}")
            return ExtractionResult(records=records, diagnostics=diagnostics, success=True)

        except Exception as e:
            logger.error(f"Excel Extraction failed: {e}")
            import traceback
            diagnostics.append(str(e))
            diagnostics.append(traceback.format_exc())
            return ExtractionResult(success=False, diagnostics=diagnostics)
