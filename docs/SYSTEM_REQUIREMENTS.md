# SerapeumAI — System Requirements (Windows)

These requirements are practical guidance for a good experience on **Windows**. If your machine is below the minimums, the app may still run, but performance will degrade.

---

## Supported operating systems
- Windows 10 (64-bit)
- Windows 11 (64-bit)

---

## Python
- **Recommended:** Python 3.11
- **Minimum:** Python 3.10
- **Also works in many setups:** Python 3.12 (if all dependencies support it)

> If you have multiple Python installs, make sure you consistently run SerapeumAI with the same one.

---

## Hardware

### CPU
- **Minimum:** modern 4-core CPU
- **Recommended:** 6–12 cores for smoother processing and indexing

### RAM
- **Minimum:** 16 GB
- **Recommended:** 32 GB for medium/large projects

Why RAM matters:
- Ingestion/indexing can temporarily use a lot of memory.
- Local AI models may also use significant memory depending on size.

### GPU (optional but recommended)
A GPU is not required, but it helps a lot for:
- Vision/OCR-heavy projects (scanned PDFs, drawings)
- Faster responses during chat

Practical guidance:
- **Recommended:** NVIDIA GPU with **6 GB+ VRAM**
- **Better:** 8–12 GB VRAM if you plan to use larger models frequently

If you don’t have a GPU:
- Expect slower vision processing and slower chat
- You can still use smaller models effectively

### Storage
- **Minimum free disk:** 10 GB
- **Recommended:** 25+ GB if you plan to keep multiple models and large projects

Storage use comes from:
- Your project documents (often large)
- Model files (can be several GB each)
- Caches and extracted text/indexes

### Disk speed
- SSD is strongly recommended.
- HDD can work, but ingestion/indexing will be much slower.

---

## Display
- Recommended: 1920×1080 or higher
- The UI may still work at lower resolutions, but panels can feel cramped.

---

## Folder access and permissions
SerapeumAI needs read/write access to:
- Your project folder(s)
- Its local storage folder (for cache, indexes, exports)

If your project folder is in a restricted location:
- Move it to a normal user folder (Documents / Desktop / a dedicated Projects folder).

---

## Internet access
- The core workflows are designed for local use.
- You may need internet only for optional activities such as downloading models (depending on your setup).

---

## Performance tiers (rule of thumb)

### Tier A — Comfortable
- 32 GB RAM
- SSD
- 8 GB+ VRAM GPU

### Tier B — Usable
- 16 GB RAM
- SSD
- No GPU or entry GPU

### Tier C — Struggle zone
- 8 GB RAM
- HDD
- No GPU  
Expect long waits and frequent slowdowns.
