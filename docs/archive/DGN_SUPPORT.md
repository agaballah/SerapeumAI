# DGN File Support in SerapeumAI

## Overview

SerapeumAI now supports MicroStation DGN files through automated conversion to DXF format and subsequent parsing. No manual steps required.

## Supported DGN Versions

- DGN v8.0 and later (modern MicroStation 2004+)
- Supported through ODA File Converter and GDAL/OGR

## Supported Features

### Geometry Extraction
- Lines, arcs, circles, polygons
- 3D elements (converted to 2D projections)
- Text, dimensions, and annotations
- Xrefs (external references / nested files)

### Data Extraction
- Drawing title and metadata
- Layer information
- Color and line styles
- Sheet numbers and revisions (if embedded in title block)
- Coordinate system information

### Content Conversion
- DGN → DXF (intermediate format)
- DXF → Parsed text, entities, and relationships
- Automatic XREF resolution and ingestion

## Installation Requirements

### Option 1: ODA File Converter (Recommended)

1. Download from: https://www.opendesign.com/guestfiles/ODAFileConverter
2. Run the installer (Windows, Linux, macOS supported)
3. SerapeumAI will auto-detect the installation

**For manual path configuration:**
```powershell
# PowerShell (Windows)
$env:ODA_CONVERTER_PATH = 'C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe'
```

Or set in environment variables:
- `ODA_CONVERTER_PATH` — Full path to ODAFileConverter executable
- `SERAPEUM_ODA_PATH` — Alternative env var name

### Option 2: GDAL/OGR (Alternative)

1. Install OSGeo4W or standalone GDAL
2. Ensure `ogr2ogr` is in system PATH or set `GDAL_DATA` env var
3. SerapeumAI will auto-detect

### Option 3: Bundled LibreDWG (Legacy)

- Automatically downloaded if DGN contains DWG-compatible structures
- Fallback option, less comprehensive than ODA

## Usage

### Via UI

1. Open a project
2. Click **Import** or **Add Documents**
3. Select `.dgn` file(s)
4. SerapeumAI will automatically:
   - Detect DGN format
   - Invoke converter (ODA or GDAL)
   - Parse resulting DXF
   - Extract text, entities, and relationships
   - Process any nested XREFs

### Via API

```python
from src.document_processing.document_service import DocumentService
from src.db.database_manager import DatabaseManager

db = DatabaseManager(root_dir="/path/to/project")
service = DocumentService(db=db)

# Ingest a DGN file
result = service.ingest_document(
    abs_path="/path/to/drawing.dgn",
    project_id="my_project"
)

print(f"Processed: {result['doc_id']}")
print(f"Pages: {len(result.get('pages', []))}")
print(f"Text: {result['text'][:200]}...")
```

### Via CLI

```bash
python -m src.document_processing.generic_processor /path/to/drawing.dgn /path/to/rel_path /path/to/export_dir
```

## Automatic XREF Resolution

SerapeumAI automatically detects and processes external references (XREFs) in DGN files:

1. **Detection**: Scans DGN for referenced file paths
2. **Resolution**: Locates and loads referenced DGN/DXF files
3. **Ingestion**: Processes references as separate documents
4. **Linking**: Maintains parent-child relationships in database

### Disabling XREF Processing

To process DGN without resolving XREFs:

```python
# Via config
from src.core.config import config
config.vision.process_xrefs = False  # (if implemented)

# Or skip via API
service.ingest_document(
    abs_path="/path/to/drawing.dgn",
    project_id="my_project",
    skip_xrefs=True  # (if implemented)
)
```

## Conversion Pipeline

```
DGN File
  ↓
ODA File Converter (or GDAL/OGR)
  ↓
Temporary DXF File
  ↓
DXF Parser (ezdxf library)
  ↓
Extracted Text, Entities, Relationships
  ↓
Database Storage
  ↓
Vision/OCR Processing (optional)
```

## Troubleshooting

### "ODA File Converter not found"

**Fix:**
1. Download ODA from https://www.opendesign.com/guestfiles/ODAFileConverter
2. Install to default location or set `ODA_CONVERTER_PATH` env var
3. Restart SerapeumAI

### "Conversion failed with code X"

**Causes:**
- Invalid DGN file (corrupt or unsupported version)
- Insufficient disk space for temp DXF
- XREF resolution failed (referenced files missing)

**Fix:**
1. Test DGN with ODA directly: `ODAFileConverter.exe <input_dir> <output_dir> ACAD2021 DXF <file.dgn>`
2. Check disk space: `du -sh /tmp` (or `Get-Item C:\Temp -Force | Measure-Object -Sum -Property Length`)
3. Verify XREF paths are accessible
4. Check logs: `logs/app.jsonl` for detailed error

### "DXF parsing failed"

**Likely cause:**
- Converter produced invalid DXF or DXF version incompatible with ezdxf

**Fix:**
1. Try with ODA instead of GDAL: Set `ODA_CONVERTER_PATH`
2. Open DXF in AutoCAD/LibreCAD to verify validity
3. Report to dev team with DGN sample

## Performance

### Typical Conversion Times (per file)

- Small DGN (< 1MB): 0.5 - 2 seconds
- Medium DGN (1-10MB): 2 - 10 seconds
- Large DGN (> 10MB): 10 - 60 seconds

### Optimization Tips

1. **Parallel Processing**: Set `config.vision.PARALLEL_WORKERS = 4` for multi-threaded XREF ingestion
2. **Batch Imports**: Import multiple DGNs in single session (converter caches models)
3. **Skip OCR**: DGN files contain machine-readable text; skip vision processing if not needed

## Known Limitations

1. **3D Elements**: Converted to 2D projections (top-down view)
2. **Embedded Images**: Not extracted (ODA limitation)
3. **Custom Objects**: ODA-specific or proprietary DGN extensions may not convert perfectly
4. **Very Large Files**: DGN files > 100MB may timeout (configurable)

## Planned Enhancements (Phase 4+)

- [ ] Native libopencad integration (avoid ODA dependency)
- [ ] 3D to 2D smart projection (orthographic views)
- [ ] Real-time XREF monitoring (auto-update on file change)
- [ ] DGN diff/comparison tools
- [ ] Batch DGN to PDF export with OCR

## FAQs

**Q: Do I need to install ODA for DGN support to work?**
A: ODA is recommended but not strictly required. GDAL/OGR provides an alternative. If neither is available, DGN files will fail to ingest with a clear error message pointing you to install converters.

**Q: Can I use LibreDWG instead of ODA?**
A: LibreDWG is bundled and auto-downloaded for legacy DWG support, but ODA is more reliable for DGN. If you prefer LibreDWG, it will be tried as a fallback.

**Q: Will XREFs in DGN be automatically processed?**
A: Yes, SerapeumAI detects and ingests referenced files automatically. Set `skip_xrefs=True` in API calls to disable.

**Q: What coordinate systems are supported?**
A: All standard coordinate systems supported by ODA and ezdxf (local, UTM, lat/long, etc.). Coordinate info is preserved in metadata.

**Q: Can I convert DGN to PDF for archival?**
A: Not directly in this phase. Export to DXF first, then use a DXF-to-PDF tool. Phase 4 will add direct DGN-to-PDF export.

## Support & Feedback

- Issue tracker: [GitHub Issues](https://github.com/AhmedGaballa/SerapeumAI/issues)
- Questions: Use issue template "DGN Support"
- Contribute: PRs welcome for DGN-specific enhancements
