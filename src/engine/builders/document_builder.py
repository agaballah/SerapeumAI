import logging
import hashlib
import json
import re
from typing import List, Dict, Any, Optional, Iterable, Tuple

from src.domain.facts.models import Fact, FactStatus, FactInput, ValueType
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

# Purely deterministic structural facts: derived from row counts, file metadata, and
# explicit extractor text matches. These can be auto-promoted to VALIDATED because the
# builder is not inferring beyond what is already present in persisted extraction output.
_STRUCTURAL_FACT_TYPES = frozenset({
    "document.page_count",
    "document.has_text",
    "document.profile",
    "document.scope_item",
    "document.area_approx",
    "document.includes_component",
    "document.design_obligation",
    "document.vendor_basis",
    "document.requirement",
})


class DocumentBuilder:
    """
    Builder: DOCUMENT
    Consumes live runtime evidence tables:
      - pdf_pages
      - doc_blocks
      - documents
      - entity_nodes (optional)
    Produces evidence-backed document facts for one file_version snapshot.
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def build(self, project_id: str, snapshot_id: str) -> List[Fact]:
        now = self.db._ts()
        doc_id = self._resolve_doc_id(snapshot_id)
        if not doc_id:
            logger.warning("DocumentBuilder: could not resolve doc_id for snapshot %s", snapshot_id)
            return []

        doc = self._query_one_safe(
            """
            SELECT doc_id, file_name, doc_title, doc_type, rel_path, content_text
            FROM documents
            WHERE doc_id = ?
            LIMIT 1
            """,
            (doc_id,)
        ) or {}

        pdf_pages = self._query_all_safe(
            """
            SELECT page_id, file_version_id, page_no, text_content, metadata_json
            FROM pdf_pages
            WHERE file_version_id = ?
            ORDER BY page_no
            """,
            (snapshot_id,)
        )

        blocks = self._query_all_safe(
            """
            SELECT doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type
            FROM doc_blocks
            WHERE doc_id = ?
            ORDER BY page_index, block_id
            """,
            (doc_id,)
        )

        entity_rows = self._query_all_safe(
            """
            SELECT value
            FROM entity_nodes
            WHERE project_id = ? AND doc_id = ?
            ORDER BY id
            LIMIT 25
            """,
            (project_id, doc_id)
        )

        page_count = len(pdf_pages)
        block_count = len(blocks)
        text_chars = sum(len((r.get("text_content") or "").strip()) for r in pdf_pages)
        has_text = text_chars > 0

        headings = []
        for b in blocks:
            title = (b.get("heading_title") or "").strip()
            if title:
                headings.append({
                    "page_index": b.get("page_index"),
                    "heading_number": b.get("heading_number"),
                    "heading_title": title,
                })
        headings = headings[:10]

        entities = []
        seen = set()
        for r in entity_rows:
            val = (r.get("value") or "").strip()
            if val and val not in seen:
                seen.add(val)
                entities.append(val)

        abstract = self._build_abstract(doc, pdf_pages, blocks)

        facts: List[Fact] = []

        def make_fact(fact_suffix: str, fact_type: str, value_type: ValueType, value: Any):
            fact = Fact(
                fact_id=f"fact_doc_{fact_suffix}_{snapshot_id[:8]}",
                project_id=project_id,
                fact_type=fact_type,
                subject_kind="document",
                subject_id=doc_id,
                as_of={"file_version_id": snapshot_id, "doc_id": doc_id},
                value_type=value_type,
                value=value,
                # Structural/deterministic facts are auto-promoted to VALIDATED.
                # LLM-derived facts (abstract, entities, headings) stay CANDIDATE.
                status=(
                    FactStatus.VALIDATED
                    if fact_type in _STRUCTURAL_FACT_TYPES
                    else FactStatus.CANDIDATE
                ),
                method_id="document_builder_v1",
                created_at=now,
                updated_at=now
            )
            return fact

        f_page_count = make_fact("page_count", "document.page_count", ValueType.NUM, page_count)
        f_page_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "pdf_pages", "doc_id": doc_id}))
        facts.append(f_page_count)

        f_block_count = make_fact("block_count", "document.block_count", ValueType.NUM, block_count)
        f_block_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "doc_blocks", "doc_id": doc_id}))
        facts.append(f_block_count)

        f_has_text = make_fact("has_text", "document.has_text", ValueType.BOOL, has_text)
        f_has_text.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "pdf_pages", "doc_id": doc_id}))
        facts.append(f_has_text)

        profile_value = {
            "file_name": doc.get("file_name"),
            "doc_title": doc.get("doc_title"),
            "doc_type": doc.get("doc_type"),
            "rel_path": doc.get("rel_path"),
        }
        f_profile = make_fact("profile", "document.profile", ValueType.JSON, profile_value)
        f_profile.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "documents", "doc_id": doc_id}))
        facts.append(f_profile)

        if headings:
            f_headings = make_fact("headings", "document.headings", ValueType.JSON, headings)
            f_headings.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "doc_blocks", "doc_id": doc_id}))
            facts.append(f_headings)

        if entities:
            f_entities = make_fact("entities", "document.entities", ValueType.JSON, entities)
            f_entities.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "entity_nodes", "doc_id": doc_id}))
            facts.append(f_entities)

        if abstract:
            f_abstract = make_fact("abstract", "document.abstract", ValueType.TEXT, abstract)
            f_abstract.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "doc_blocks", "doc_id": doc_id}))
            facts.append(f_abstract)

        semantic_facts = self._build_semantic_document_facts(
            project_id=project_id,
            snapshot_id=snapshot_id,
            doc_id=doc_id,
            blocks=blocks,
            pdf_pages=pdf_pages,
            now=now,
        )
        facts.extend(semantic_facts)

        logger.info(
            "DocumentBuilder built %s facts for doc_id=%s snapshot=%s",
            len(facts), doc_id, snapshot_id
        )
        return facts

    def _resolve_doc_id(self, snapshot_id: str) -> Optional[str]:
        """
        Resolve doc_id from a snapshot_id (file_version_id) using the live v14 schema.

        Live v14 file_versions columns: file_version_id, file_id, sha256, source_path.
        There is NO doc_id column on file_versions or pages.
        The authoritative join is the same one used by ExtractJob:
            documents.(file_name|abs_path) = file_versions.source_path
        Fallback: if doc_id was synthesised as 'doc_{file_version_id}', recover it
        from doc_blocks or derive it directly.
        """
        # 1. Source-path join (mirrors ExtractJob's own doc_id discovery)
        row = self._query_one_safe(
            """
            SELECT d.doc_id
            FROM documents d
            JOIN file_versions fv
              ON d.file_name = fv.source_path OR d.abs_path = fv.source_path
            WHERE fv.file_version_id = ?
            LIMIT 1
            """,
            (snapshot_id,)
        )
        if row and row.get("doc_id"):
            return row["doc_id"]

        # 2. ExtractJob synthetic fallback: doc_id = f"doc_{file_version_id}"
        #    Check whether doc_blocks carries that id (inserted during same extraction run).
        synthetic = f"doc_{snapshot_id}"
        row = self._query_one_safe(
            "SELECT doc_id FROM doc_blocks WHERE doc_id = ? LIMIT 1",
            (synthetic,)
        )
        if row and row.get("doc_id"):
            return row["doc_id"]

        # 3. Confirm via pdf_pages: if pages exist for this snapshot, the synthetic id is valid.
        row = self._query_one_safe(
            "SELECT 1 FROM pdf_pages WHERE file_version_id = ? LIMIT 1",
            (snapshot_id,)
        )
        if row:
            return synthetic

        return None

    def _build_abstract(self, doc: Dict[str, Any], pdf_pages: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> str:
        parts = []

        title = (doc.get("doc_title") or doc.get("file_name") or "").strip()
        if title:
            parts.append(title)

        heading_titles = []
        for b in blocks:
            h = (b.get("heading_title") or "").strip()
            if h and h not in heading_titles:
                heading_titles.append(h)
            if len(heading_titles) >= 3:
                break
        if heading_titles:
            parts.append("Headings: " + " | ".join(heading_titles))

        text_snippets = []
        for p in pdf_pages:
            txt = (p.get("text_content") or "").strip()
            if txt:
                txt = " ".join(txt.split())
                text_snippets.append(txt[:280])
            if len(text_snippets) >= 2:
                break
        if text_snippets:
            parts.append(" ".join(text_snippets))

        abstract = " -- ".join(x for x in parts if x).strip()
        return abstract[:1200]

    def _query_one_safe(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        try:
            row = self.db.execute(sql, params).fetchone()
            return dict(row) if row else None
        except Exception:
            return None

    def _query_all_safe(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        try:
            rows = self.db.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _build_semantic_document_facts(
        self,
        project_id: str,
        snapshot_id: str,
        doc_id: str,
        blocks: List[Dict[str, Any]],
        pdf_pages: List[Dict[str, Any]],
        now: str,
    ) -> List[Fact]:
        """Emit compact semantic document facts from explicit extracted text only."""
        lines = list(self._iter_semantic_lines(blocks=blocks, pdf_pages=pdf_pages))
        if not lines:
            return []

        seen: set[Tuple[str, str]] = set()
        facts: List[Fact] = []

        def add_fact(fact_type: str, value_type: ValueType, value: Any, source_text: str, key_hint: str) -> None:
            norm_value = json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            dedupe_key = (fact_type, norm_value.strip().lower())
            if dedupe_key in seen:
                return
            seen.add(dedupe_key)

            stable_key = hashlib.sha1(f"{doc_id}|{fact_type}|{key_hint}|{norm_value}".encode("utf-8")).hexdigest()[:12]
            fact = Fact(
                fact_id=f"fact_{stable_key}",
                project_id=project_id,
                fact_type=fact_type,
                subject_kind="document",
                subject_id=doc_id,
                as_of={"file_version_id": snapshot_id, "doc_id": doc_id},
                value_type=value_type,
                value=value,
                status=FactStatus.VALIDATED,
                confidence=0.95,
                method_id="document_builder.semantic_extract.v1",
                created_at=now,
                updated_at=now,
            )
            fact.inputs.append(
                FactInput(
                    file_version_id=snapshot_id,
                    location={"table": "doc_blocks", "doc_id": doc_id, "snippet": source_text[:500]},
                )
            )
            facts.append(fact)

        for line in lines:
            lower = line.lower()

            area_match = re.search(
                r"(?:\barea\s+is\s+|\b)(?P<num>\d+(?:\.\d+)?)\s*sq(?:uare)?\s*m(?:eters?)?(?:\s+(?:approx\.?|approximately))?",
                lower,
                re.I,
            )
            if area_match:
                num = area_match.group("num")
                if num:
                    add_fact("document.area_approx", ValueType.JSON, {"area": float(num), "approx": True}, line, f"area:{num}")

            if " in scope" in lower or "inscope" in lower:
                item = re.sub(r"\b(?:is|are)\s+in\s*scope\b", "", line, flags=re.I)
                item = re.sub(r"\binscope\b", "", item, flags=re.I)
                item = self._normalize_item(item)
                if item:
                    add_fact("document.scope_item", ValueType.TEXT, item, line, f"scope:{item}")

            includes_match = re.search(r"\b(?:scope|scopes?)\s+includes?\s+(.+)$", line, re.I)
            if includes_match:
                component = self._normalize_item(includes_match.group(1))
                if component:
                    add_fact("document.includes_component", ValueType.TEXT, component, line, f"includes:{component}")

            if re.search(r"\b(?:includes?\s+detailed\s+design|detailed\s+design)\b", lower, re.I):
                add_fact("document.design_obligation", ValueType.TEXT, "detailed design required", line, "design-obligation:detailed-design")

            requirement_patterns = [
                r"\bcontractor\s+shall\s+consider\b.+$",
                r"\bshall\s+consider\b.+$",
                r"\bshall\b\s+.+$",
                r"\bmust\b\s+.+$",
                r"\brequired\s+to\b\s+.+$",
            ]
            for pattern in requirement_patterns:
                m = re.search(pattern, line, re.I)
                if not m:
                    continue
                requirement = self._normalize_phrase(m.group(0))
                if requirement:
                    add_fact("document.requirement", ValueType.TEXT, requirement, line, f"req:{requirement}")
                vendor_match = re.search(r"\bas\s+per\s+(.+)$", m.group(0), re.I)
                if vendor_match:
                    vendor_basis = self._normalize_phrase(vendor_match.group(1))
                    if vendor_basis:
                        add_fact("document.vendor_basis", ValueType.TEXT, vendor_basis, line, f"vendor:{vendor_basis}")
                break

        return facts

    def _iter_semantic_lines(
        self,
        blocks: List[Dict[str, Any]],
        pdf_pages: List[Dict[str, Any]],
    ) -> Iterable[str]:
        seen: set[str] = set()
        for block in blocks:
            text = (block.get("text") or block.get("block_text") or "").strip()
            if not text:
                continue
            for part in re.split(r"[\n\r]+|\s*•\s*|\s*\*\s*", text):
                line = self._normalize_phrase(part)
                if len(line) < 8:
                    continue
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                yield line
        for page in pdf_pages:
            text = (page.get("text_content") or "").strip()
            if not text:
                continue
            for part in re.split(r"[\n\r]+|\s*•\s*|\s*\*\s*", text):
                line = self._normalize_phrase(part)
                if len(line) < 8:
                    continue
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                yield line

    def _normalize_item(self, text: str) -> str:
        text = self._normalize_phrase(text)
        text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.I)
        text = re.sub(r"\bapprox(?:\.|imately)?\b", "", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip(" ,.;:-")
        return text

    def _normalize_phrase(self, text: str) -> str:
        text = " ".join((text or "").replace("\xa0", " ").split())
        return text.strip(" \t\r\n-•*")
