# Quick Start: CAD/BIM File Processing

## Installation

```bash
# For IFC (BIM) support
pip install ifcopenshell

# For DXF (AutoCAD) support
pip install ezdxf

# Optional - Better PPT extraction
pip install python-pptx
```

## Test Your Installation

```bash
# Test all processors
python test_all_processors.py

# Test CAD processors specifically
python test_cad_processors.py
```

## Use in Your Code

```python
from src.document_processing.generic_processor import GenericProcessor

# Initialize
processor = GenericProcessor()

# Process any supported file
result = processor.process(
    abs_path="/path/to/file.ifc",  # or .dxf, .pdf, .docx, etc.
    rel_path="file.ifc",
    export_root="/path/to/exports"
)

# Access extracted data
print(result['text'])        # Human-readable text
print(result['meta'])        # Metadata (layers, elements, etc.)
print(result['pages'])       # Page/slide data (if applicable)
```

## Supported File Types

✅ PDF, Word (.docx/.doc), Excel (.xlsx/.xls/.csv), PowerPoint (.pptx/.ppt)  
✅ Images (.jpg/.png/.tif) with OCR  
✅ IFC (BIM models) - NEW!  
✅ DXF (AutoCAD) - NEW!  

## Coverage: 76% overall data extraction
