# -*- coding: utf-8 -*-
import os
import subprocess
import logging
import tempfile
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class ODAConverterNotFound(Exception):
    """Raised when ODA File Converter executable is not found on this system.

    Install ODA File Converter from: https://www.opendesign.com/guestfiles/oda_file_converter
    or set the ODA_CONVERTER_PATH environment variable to its location.
    """
    pass


class ODAConverter:
    """
    Wrapper for ODA File Converter (formerly DWG TrueView / Teigha).
    Used to convert DGNv8 and DWG files to DXF for parsing.
    """

    def __init__(self, converter_path: Optional[str] = None):
        self.converter_path = converter_path or self._find_converter()
        if self.converter_path:
            logger.info(f"[ODAConverter] Using converter at: {self.converter_path}")
        else:
            logger.warning("[ODAConverter] ODA File Converter not found. DGN/DWG support will be limited.")

    def _find_converter(self) -> Optional[str]:
        """Try to locate ODAFileConverter in common locations or env vars."""
        # 1. Environment variables
        env_paths = [
            os.environ.get("ODA_CONVERTER_PATH"),
            os.environ.get("SERAPEUM_ODA_PATH"),
        ]
        for p in env_paths:
            if p and os.path.exists(p):
                return p

        # 2. Windows default locations
        if os.name == "nt":
            program_files = [
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            ]
            for pf in program_files:
                oda_root = os.path.join(pf, "ODA")
                if os.path.exists(oda_root):
                    # Search recursively for the exe
                    for root, dirs, files in os.walk(oda_root):
                        if "ODAFileConverter.exe" in files:
                            return os.path.join(root, "ODAFileConverter.exe")
        
        # 3. Linux/macOS path
        return shutil.which("ODAFileConverter")

    def is_available(self) -> bool:
        return self.converter_path is not None and os.path.exists(self.converter_path)

    def convert_to_dxf(self, input_path: str, output_version: str = "ACAD2018") -> Optional[str]:
        """
        Convert a CAD file (DGN/DWG) to DXF.
        The converter requires input/output DIRECTORIES, so we use temp folders.
        """
        if not self.is_available():
            logger.error("[ODAConverter] Cannot convert: ODA File Converter not found.")
            return None

        if not os.path.exists(input_path):
            logger.error(f"[ODAConverter] Input file not found: {input_path}")
            return None

        # ODA converter works on directories
        with tempfile.TemporaryDirectory() as in_dir, tempfile.TemporaryDirectory() as out_dir:
            file_name = os.path.basename(input_path)
            shutil.copy2(input_path, os.path.join(in_dir, file_name))
            
            # Command: ODAFileConverter <input_dir> <output_dir> <out_ver> <out_format> <recursive> <filter>
            # Example: ODAFileConverter "C:\in" "C:\out" "ACAD2018" "DXF" "0" "*.dgn"
            cmd = [
                self.converter_path,
                in_dir,
                out_dir,
                output_version,
                "DXF",
                "0",  # Don't recurse
                "*.dgn" if input_path.lower().endswith(".dgn") else "*.dwg"
            ]

            try:
                logger.info(f"[ODAConverter] Running conversion for {file_name}...")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    logger.error(f"[ODAConverter] Conversion failed with code {result.returncode}")
                    logger.debug(f"STDOUT: {result.stdout}")
                    logger.debug(f"STDERR: {result.stderr}")
                    return None

                # Find result file
                base_no_ext = os.path.splitext(file_name)[0]
                dxf_path = os.path.join(out_dir, f"{base_no_ext}.dxf")
                
                if os.path.exists(dxf_path):
                    # Move to a stable temp location or caller handles cleanup
                    final_path = os.path.join(tempfile.gettempdir(), f"serapeum_{base_no_ext}_{os.urandom(4).hex()}.dxf")
                    shutil.move(dxf_path, final_path)
                    logger.info(f"[ODAConverter] Successfully converted to {final_path}")
                    return final_path
                else:
                    logger.error(f"[ODAConverter] Conversion finished but output DXF not found in {out_dir}")
                    return None

            except subprocess.TimeoutExpired:
                logger.error(f"[ODAConverter] Conversion timed out for {file_name}")
                return None
            except Exception as e:
                logger.error(f"[ODAConverter] Unexpected error during conversion: {e}")
                return None

def get_oda_executable() -> str:
    """Helper for legacy tests to find the ODA converter. Raises ODAConverterNotFound if missing."""
    exe = ODAConverter().converter_path
    if not exe:
        raise ODAConverterNotFound("ODA File Converter not found. Download from https://www.opendesign.com/guestfiles/oda_file_converter")
    return exe

def convert_dgn_to_dxf(input_path: str) -> Optional[str]:
    """Helper for legacy tests to convert a DGN file."""
    return ODAConverter().convert_to_dxf(input_path)
