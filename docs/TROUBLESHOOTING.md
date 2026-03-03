# SerapeumAI — Troubleshooting

This guide covers the most common issues:
- App doesn’t start
- Model not detected / AI not responding
- Performance issues

If you can reproduce a problem reliably, capture:
- What you clicked
- The exact error message (copy/paste if possible)
- What type of file/project triggered it (PDF, scan, DXF, etc.)

---

## 1) App doesn’t start

### Symptoms
- You run the app and nothing appears
- A window flashes and closes
- You see a “missing module” or “failed to import” type message

### Likely causes
- Python version mismatch
- Dependencies not installed or installed in a different environment
- Antivirus or Windows security blocking execution
- The app can’t access its folders (permissions)

### Fix checklist
1) Confirm you are on **Windows 10/11 (64-bit)**.
2) Confirm you are using a supported Python version (see `SYSTEM_REQUIREMENTS.md`).
3) Make sure you are running from the **project folder** (the folder that contains `run.py`).
4) If Windows blocks it:
   - Check Windows Security → Protection history
   - Allow the app if it was quarantined
5) Try a clean reboot (it clears locked files and stuck GPU drivers).
6) If you see an error message, keep it — it’s usually the fastest clue.

---

## 2) Model not detected (or AI not responding)

### Symptoms
- Chat says the model is unavailable
- Model selector is empty
- You click “Analyze” or send a chat message and nothing returns

### Likely causes
- No model selected
- Model file missing or moved
- Model is too large for available RAM/VRAM
- Another process is already using the GPU heavily

### Fix checklist
1) Open **Settings → Model** (or the model selector area).
2) Confirm a model is selected.
3) If the UI shows a model path or name:
   - Confirm it still exists
   - If you moved models to a new folder, reselect the model
4) If the app provides a “test model” or “refresh models” action, run it.
5) If the model is large:
   - Switch to a smaller model
   - Close other heavy apps
   - Retry

### If the AI “hangs”
- Cancel/stop the request (if a cancel button exists), then retry with a shorter question.
- Reduce scope:
  - Ask about one document instead of the full project
  - Ask for a summary first, then ask details

---

## 3) Performance issues

### Symptoms
- Chat responses take a long time
- The UI becomes laggy during processing
- Vision/OCR tasks never seem to finish

### Causes
- Project is large (hundreds of documents)
- Files are scanned PDFs/images (vision is expensive)
- Running on CPU-only hardware
- Disk is slow (HDD) or low on free space

### Fix checklist
1) Check disk free space (10–25 GB+ recommended depending on your project).
2) Use an SSD if possible.
3) If your build has a performance setting:
   - Prioritize **Chat** when you need responsiveness
   - Prioritize **Processing** when you want ingestion to finish faster
4) Reduce project size:
   - Start with a smaller folder subset
   - Ingest and verify in phases (specs first, then drawings, etc.)
5) Prefer smaller models when:
   - You need speed
   - You are on CPU-only hardware

---

## 4) PDF text is empty

### Symptoms
- A PDF preview shows pages, but extracted text is blank
- Chat can’t find answers from that PDF

### Likely causes
- The PDF is scanned (image-based)
- OCR/vision processing hasn’t run yet
- The scan quality is low (faint text, skewed pages)

### Fix checklist
1) Ensure processing has run for the project (ingest/vision/indexing).
2) If there’s a vision/OCR toggle, ensure it is enabled.
3) Try a better-quality PDF if available (native text PDFs work best).

---

## 5) Compliance results look wrong

### Symptoms
- Findings don’t match the document
- Incorrect “fail” flags
- Missing obvious requirements

### Likely causes
- Missing documents in the project folder
- Processing incomplete
- Ambiguous requirement language or incomplete context

### Fix checklist
1) Open the cited document/page and verify the source.
2) Check if the relevant document was actually ingested.
3) Rerun processing after adding missing files.
4) Ask chat to explain the finding and cite the exact evidence.

---

## 6) Graph view is empty (or unhelpful)

### Symptoms
- No nodes or links appear
- Graph is a single cluster with no structure

### Likely causes
- Cross-document linking hasn’t been built yet
- The project doesn’t contain explicit references
- Documents are images without OCR

### Fix checklist
1) Run processing fully (including vision/OCR if needed).
2) Start with a smaller subset (specs only, then add drawings).
3) Use filters if available (by folder, file type, or discipline).

---

## 7) When to escalate
If you still can’t solve it, capture:
- The exact error text
- Steps to reproduce (click-by-click)
- The smallest project folder that reproduces the issue

That combination makes debugging dramatically faster.
