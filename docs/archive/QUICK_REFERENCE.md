# Serapeum AECO Assistant — Quick Reference

## 🚀 Getting Started in 5 Minutes

### 1. Prerequisites
```bash
# Ensure Python 3.11 is installed
python --version

# Install dependencies
pip install -r requirements.txt
```

### 2. Model Download (Automatic)
```bash
# On first launch, Serapeum will automatically download:
# - Qwen2-VL-7B-Instruct (4.6 GB GGUF model)
# - Saved to: ~/.serapeum/models/
# 
# No manual LLM setup required!
# Model runs embedded in the application.
```

### 3. Launch Application
```bash
cd D:\SerapeumAI
python run.py
```

### 4. Create Your First Project
1. Click **"New Project"**
2. Enter project name (e.g., "Hospital Renovation")
3. Select folder containing your documents
4. Click **"Run Pipeline"** to ingest files

---

## 📋 Common Tasks

### Ingest New Documents
```python
# Via GUI
1. Open project
2. Add files to project folder
3. Click "Run Pipeline" > "Ingest"

# Via CLI
python run_pipeline_headless.py --project_dir "path/to/project"
```

### Run Compliance Check
```bash
# Ensure standards database is populated
python scripts/seeds/sample_standards_data.py

# Run compliance analysis
# Via GUI: Click "Run Pipeline" > "Compliance"
# Via CLI: python run_qa_tests.py
```

### Chat with Project Data
1. Open **Chat Panel** tab
2. Select your **Role** (Contractor/Owner/PMC/Consultant)
3. Select your **Specialty** (Arch/Str/Mech/Elec)
4. Type query or attach files
5. LLM responds with RAG-enhanced context

### Configure LLM Settings
1. Click **Settings** button in Chat Panel
2. Update:
   - Model Path (default: auto-detected)
   - GPU Acceleration (default: enabled if available)
   - GPU Layers (0-33, affects speed vs VRAM usage)
   - n8n Webhook URL (optional)
3. Click **OK** to save

---

## 🔧 Troubleshooting

### "Model loading failed" error
**Cause**: Model file not found or insufficient RAM  
**Fix**:
```bash
# Check model exists
ls ~/.serapeum/models/qwen2-vl-7b-instruct-q4_k_m.gguf

# If missing, re-download from Settings
# Or manually download from HuggingFace:
# https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct-GGUF
```

### "Zero text extracted" from PDFs
**Cause**: Native PDF text extraction not implemented  
**Status**: Known issue (see TECHNICAL_OVERVIEW.md)  
**Workaround**: Use Vision worker (manual trigger required)

### Vision worker not running
**Cause**: Auto-trigger not implemented  
**Fix**: Click **"Vision Pass"** button (if enabled in UI)  
**Status**: Known issue

### Empty compliance results
**Cause**: Standards database is empty  
**Fix**:
```bash
python scripts/seeds/sample_standards_data.py
```

### Application crashes on startup
**Cause**: Likely undefined variable errors  
**Check**: Look for F821 errors in linter output  
**Fix**: See TECHNICAL_OVERVIEW.md > Known Issues

---

## 📁 File Locations

| Item | Path |
|------|------|
| **Application Root** | `D:\SerapeumAI\` |
| **Project Database** | `.serapeum/serapeum.sqlite3` |
| **Standards Database** | `.serapeum/standards.sqlite3` |
| **LLM Config** | `.serapeum/_context/profile.json` |
| **Logs** | `logs/serapeum.log` |
| **Exported Pages** | `.pages/` (under project folder) |

---

## 🧪 Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test suites
pytest tests/test_smoke.py -v           # Core functionality
pytest tests/test_llm_connection.py -v  # LLM connectivity
pytest tests/unit/ -v                   # Unit tests

# Linting
ruff check src scripts tests --select E9,F63,F7,F82,F821  # Critical errors
ruff check src scripts tests                               # All issues
ruff check src scripts tests --fix                         # Auto-fix

# Dead code detection
vulture src scripts
```

---

## 📊 Supported File Formats

### ✅ Fully Supported
- **PDF** (with OCR fallback)
- **Word**: `.docx`, `.doc`
- **Excel**: `.xlsx`, `.xls`, `.csv`
- **PowerPoint**: `.pptx`, `.ppt`
- **Images**: `.jpg`, `.png`, `.tif`
- **CAD**: `.dxf` (requires `ezdxf`)
- **BIM**: `.ifc` (requires `ifcopenshell`)

### ⚙️ Requires Setup
- **DWG**: Convert to DXF using ODA File Converter ([guide](docs/DWG_SUPPORT.md))
- **Revit (.rvt)**: Export to IFC manually ([guide](docs/REVIT_SUPPORT.md))

---

## 💡 Pro Tips

### Speed Up Ingestion
```python
# Process only new files by checking database first
# (Currently re-processes all files — known issue)
```

### Improve RAG Accuracy
1. Ensure Vision worker has run (populates OCR text)
2. Use specific queries instead of vague questions
3. Attach relevant files directly to chat

### Verify Calculations
```python
# Chat example:
"Calculate the total concrete volume for slabs on levels 1-3"

# LLM will use CalculatorTool for accurate math
# Returns: {"result": 1234.56, "expression": "..."}
```

### Export Analysis Results
```python
# Currently manual
# Future: Export to PDF/Excel via reporting module
```

---

## 🐛 Reporting Bugs

**Before reporting, check**:
1. Is LM Studio running?
2. Is the project database initialized?
3. Have you run `ruff check` for syntax errors?

**Include in bug report**:
- Screenshots
- `logs/serapeum.log` (last 50 lines)
- Steps to reproduce
- Python version (`python --version`)

---

## 📞 Support Resources

- **Technical Overview**: [TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md)
- **Codebase Audit**: [codebase_audit.md](codebase_audit.md)
- **Known Issues**: See TECHNICAL_OVERVIEW.md § Known Issues

---

**Last Updated**: November 2025
