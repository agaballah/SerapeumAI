# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0

"""
test_dgn_integration.py — DGN file processing integration tests
---------------------------------------------------------------
Tests for DGN→DXF conversion and parsing via generic processor.
"""

import os
import tempfile
import shutil
import pytest


class TestDGNIntegration:
    """Test DGN file support."""

    def test_dgn_processor_available(self):
        """Test that DGN processor exists."""
        from src.document_processing import dgn_processor
        assert dgn_processor is not None
        assert hasattr(dgn_processor, 'process')

    def test_dgn_can_handle_extension(self):
        """Test DGN extension detection."""
        from src.document_processing.dgn_processor import can_handle
        
        assert can_handle("drawing.dgn") is True
        assert can_handle("drawing.DGN") is True
        assert can_handle("drawing.dxf") is False
        assert can_handle("drawing.pdf") is False

    def test_oda_converter_module_available(self):
        """Test that ODA converter module is importable."""
        from src.document_processing import oda_converter
        assert oda_converter is not None
        assert hasattr(oda_converter, 'get_oda_executable')
        assert hasattr(oda_converter, 'convert_dgn_to_dxf')

    def test_generic_processor_routes_dgn(self):
        """Test that GenericProcessor recognizes DGN extension."""
        from src.document_processing.generic_processor import GenericProcessor
        
        processor = GenericProcessor()
        assert ".dgn" in processor.DGN_EXTS

    def test_dgn_processing_error_handling(self):
        """Test that DGN processor handles errors gracefully."""
        from src.document_processing import dgn_processor
        
        # Try to process non-existent file
        result = dgn_processor.process("/nonexistent/file.dgn")
        
        # Should return error payload (not raise)
        assert result is not None
        assert isinstance(result, dict)
        assert "text" in result
        assert "meta" in result

    def test_oda_executable_detection(self):
        """Test ODA executable detection (or graceful skip if not installed)."""
        from src.document_processing.oda_converter import get_oda_executable, ODAConverterNotFound
        
        try:
            exe = get_oda_executable()
            # ODA is available
            assert exe is not None
            print(f"ODA found: {exe}")
        except ODAConverterNotFound as e:
            # ODA not installed - check error message is helpful
            assert "opendesign.com" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
