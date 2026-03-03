# DWG Support Guide

## Overview
DWG files are AutoCAD's proprietary format. To process them in Serapeum, we convert DWG → DXF using ODA File Converter.

## Installation

### 1. Download ODA File Converter
- Visit: https://www.opendesign.com/guestfiles/oda_file_converter  
- Download for Windows
- Install to default location (C:\\Program Files\\ODA\\ODAFileConverter)

### 2. Use from Command Line
```bash
# Convert DWG to DXF
"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe" 
    "D:\Drawings" 
    "D:\Drawings\Converted" 
    "ACAD2018" 
    "DXF" 
    "0" 
    "1" 
    "*.dwg"
```

### 3. Process with Serapeum
```python
import subprocess
from src.document_processing.generic_processor import GenericProcessor

# Convert DWG to DXF
subprocess.run([
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    input_folder,
    output_folder,
    "ACAD2018",
    "DXF",
    "0",
    "1",
    "*.dwg"
])

# Process the DXF
gp = GenericProcessor()
result = gp.process(
    abs_path="output/drawing.dxf",
    rel_path="drawing.dxf",
    export_root="exports/"
)
```

## Automation
Create a helper function in `src/document_processing/dwg_converter.py` to automate this process.

## Status
✅ DXF processor ready
⚠️ DWG requires ODA File Converter (free, external tool)
📝 Pathway defined, implementation straightforward
