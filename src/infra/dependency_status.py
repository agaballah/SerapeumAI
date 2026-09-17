# -*- coding: utf-8 -*-
"""
dependency_status.py — Centralized dependency health reporting.

Monitors critical optional dependencies and reports their status
to enable transparent capability visibility in the UI.

This module does NOT modify any extractor or processor.
It only reads import state and reports what is available.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DependencyStatus:
    """Health status of a single optional dependency."""
    name: str
    status: str  # "installed" | "missing" | "unavailable"
    version: str = ""
    required_for: List[str] = field(default_factory=list)
    install_command: str = ""
    error_message: str = ""
    severity: str = "info"  # "info" | "warning" | "critical"


class DependencyHealthChecker:
    """Checks and reports the health of optional dependencies."""

    # Registry of known dependencies with their metadata
    REGISTRY: Dict[str, Dict[str, str]] = {
        "ifcopenshell": {
            "required_for": [".ifc"],
            "install_command": "pip install ifcopenshell",
            "severity": "critical",
        },
        "mpxj": {
            "required_for": [".mpp"],
            "install_command": "pip install mpxj jpype1",
            "severity": "critical",
        },
        "xlrd": {
            "required_for": [".xls"],
            "install_command": "pip install xlrd",
            "severity": "critical",
        },
        "tesseract": {
            "required_for": [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"],
            "install_command": "Install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki",
            "severity": "warning",
            "check_cmd": "tesseract --version",
        },
        "poppler": {
            "required_for": [".pdf"],
            "install_command": "Install poppler from https://poppler.freedesktop.org/",
            "severity": "warning",
            "check_cmd": "pdftoppm -v",
        },
        "rapidocr": {
            "required_for": [".pdf", ".png", ".jpg"],
            "install_command": "pip install rapidocr",
            "severity": "info",
        },
    }

    @classmethod
    def check_all(cls) -> List[DependencyStatus]:
        """Check all registered dependencies and return status list."""
        results = []
        for name, meta in cls.REGISTRY.items():
            results.append(cls._check_one(name, meta))
        return results

    @classmethod
    def _check_one(cls, name: str, meta: Dict[str, str]) -> DependencyStatus:
        """Check a single dependency."""
        # Try importing the Python package
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", "unknown")
            return DependencyStatus(
                name=name,
                status="installed",
                version=str(version),
                required_for=meta.get("required_for", []),
                install_command=meta.get("install_command", ""),
                severity=meta.get("severity", "info"),
            )
        except ImportError:
            pass

        # Try system command check (for tesseract, poppler)
        check_cmd = meta.get("check_cmd")
        if check_cmd:
            import subprocess
            try:
                result = subprocess.run(
                    check_cmd.split(),
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split()[0] if result.stdout else "found"
                    return DependencyStatus(
                        name=name,
                        status="installed",
                        version=version,
                        required_for=meta.get("required_for", []),
                        install_command=meta.get("install_command", ""),
                        severity=meta.get("severity", "info"),
                    )
            except Exception:
                pass

        # Missing
        return DependencyStatus(
            name=name,
            status="missing",
            required_for=meta.get("required_for", []),
            install_command=meta.get("install_command", ""),
            severity=meta.get("severity", "info"),
        )

    @classmethod
    def get_summary(cls) -> Dict[str, int]:
        """Return counts by status."""
        deps = cls.check_all()
        counts = {"installed": 0, "missing": 0, "unavailable": 0}
        for d in deps:
            counts[d.status] = counts.get(d.status, 0) + 1
        return counts

    @classmethod
    def get_critical_missing(cls) -> List[str]:
        """Return list of critical missing dependency names."""
        return [
            d.name for d in cls.check_all()
            if d.status == "missing" and d.severity == "critical"
        ]

    @classmethod
    def get_missing_formats(cls) -> List[str]:
        """Return list of file extensions that cannot be processed."""
        missing = cls.get_critical_missing()
        formats = set()
        for name in missing:
            meta = cls.REGISTRY.get(name, {})
            for fmt in meta.get("required_for", []):
                formats.add(fmt)
        return sorted(formats)
