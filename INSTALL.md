# SerapeumAI — Installation Guide

This guide walks you through setting up SerapeumAI on a fresh machine (Windows, Linux, or macOS).

> **No virtual environment needed.** Install into your system Python or a Conda environment.

---

## ✅ Prerequisites Checklist

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 or 3.11 | 3.11 recommended — do NOT use 3.12+ |
| LM Studio CLI (`lms`) | Latest | **Required** — the app starts LM Studio automatically |
| Tesseract OCR | 5.x | Required for PDF text extraction |
| Poppler | Latest | Required for PDF rendering |
| Git | Any | For cloning the repo |

---

## Step 1 — Clone the Repo

```bash
git clone https://github.com/gaballa/SerapeumAI.git
cd SerapeumAI
```

---

## Step 2 — Install LM Studio CLI (`lms`)

The app **automatically** starts LM Studio in the background — you never need to open the GUI.
It uses the `lms` command-line tool for this.

### 🪟 Windows

```powershell
# Install the lms CLI via npm
npm install -g @lmstudio/lms
```
Or download the standalone installer from: https://lmstudio.ai/download  
After install, ensure `lms` is available in your PATH:
```powershell
lms --version
```

### 🐧 Linux / 🍎 macOS

```bash
npm install -g @lmstudio/lms
# or
curl -fsSL https://lmstudio.ai/install.sh | sh

lms --version   # verify it works
```

### Download a model (first time only)

The app needs at least one chat model. Download one now so it's ready:
```bash
# Download a small but capable model (~4GB)
lms get lmstudio-community/Qwen2.5-7B-Instruct-GGUF

# Or any other model from Hugging Face, e.g.:
# lms get bartowski/Mistral-7B-Instruct-v0.3-GGUF
```

> After installation, **do not manually start LM Studio** — the app does it automatically on launch.

---

## Step 3 — Install System Dependencies

These must be installed **before** running `pip install`. They are native system tools.

### 🪟 Windows

**Tesseract OCR:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer — tick "Add to PATH"
3. Verify: `tesseract --version`

**Poppler (for PDF rendering):**
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract and add the `bin/` folder to your PATH
3. Verify: `pdfinfo --version`

### 🐧 Linux (Ubuntu/Debian)

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-ara poppler-utils
```

### 🍎 macOS

```bash
brew install tesseract poppler
```

---

## Step 4 — Install ifcopenshell (for IFC/BIM files)

`ifcopenshell` is **not** available as a standard pip package on all platforms.

**Option A — Conda (recommended):**
```bash
conda install -c conda-forge ifcopenshell
```

**Option B — Pre-built wheel:**
1. Go to: https://github.com/IfcOpenShell/IfcOpenShell/releases
2. Download the `.whl` for your Python version + OS
3. `pip install <downloaded_file.whl>`

> Skip this step if you don't process IFC/BIM files.

---

## Step 5 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

> **Note on `llama-cpp-python`** (legacy embedded model support — optional):
> For NVIDIA GPU acceleration:
> ```bash
> pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
> ```
> For CPU-only: `pip install llama-cpp-python`

---

## Step 6 — Run the App

```bash
python run.py
```

On first launch:
- The app **auto-starts** `lms daemon up` then `lms server start` in the background
- A folder selection dialog opens → pick your project folder
- Status bar turns **green** when the project is loaded
- The app benchmarks available models and routes tasks automatically

---

## Step 7 — (Optional) Run Tests

```bash
python -m pytest src/tests/ -q
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `lms: command not found` | Install via `npm install -g @lmstudio/lms` and restart terminal |
| `tesseract not found` | Add Tesseract to PATH |
| `Unable to get page count. Is poppler installed?` | Install/add Poppler to PATH |
| LLM not responding | Check `lms server status` — app will retry automatically |
| `ModuleNotFoundError: ifcopenshell` | Follow Step 4 |
| `CUDA out of memory` | LM Studio will handle GPU layers — use a smaller/quantized model |
| App is slow on first run | Normal — it is benchmarking your models. Subsequent runs use the cached result |

---

## 💻 Hardware Recommendations

| Tier | RAM | GPU VRAM | Expected Performance |
|------|-----|----------|---------------------|
| Minimum | 16 GB | None | CPU inference only — slow but functional |
| Recommended | 32 GB | 8 GB | Fast chat & analysis |
| Optimal | 64 GB | 16–24 GB | Full vision + parallel processing |

---

*For architecture details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)*
