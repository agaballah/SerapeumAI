# SerapeumAI Troubleshooting Guide

## 🔍 Common Issues & Solutions

### 1. PDF Text Extraction Issues
**Problem**: Extracted text is empty or contains garbage characters.
**Possible Causes**:
- The PDF is a scanned image (no text layer).
- The PDF uses a non-standard encoding.
**Solution**:
1. **Enable Vision Processing**: Ensure the Vision Worker is running. It will use OCR (Tesseract) and VLM (Qwen) to extract text from images.
2. **Check Logs**: Look for `[pdf.step4]` logs to see if OCR was triggered.
3. **Verify File**: Open the PDF in a browser and try to select text. If you can't, it's an image.

### 2. Vision Worker Not Starting
**Problem**: The "Vision" status indicator remains gray or "Paused".
**Solution**:
1. **Check Pipeline Status**: The Vision Worker is automatically paused during **Analysis** and **Chat** to prevent GPU conflicts. It should resume automatically.
2. **Manual Trigger**: You can manually start the worker from the "Settings" > "Vision" menu.
3. **GPU Memory**: Ensure you have enough VRAM (6GB+). If not, switch to "CPU Mode" in `config.yaml` (slower).

### 3. "Cannot Connect to LM Studio"
**Problem**: The application shows a connection error when trying to chat or analyze.
**Solution**:
1. **Launch LM Studio**: Make sure the application is open.
2. **Start Server**: Click "Start Server" in LM Studio.
3. **Check Port**: Ensure the port is set to `1234` (default).
4. **Firewall**: Check if Windows Firewall is blocking the connection.

### 4. Application Crashes on Startup
**Problem**: The window opens and immediately closes.
**Solution**:
1. **Check Logs**: Open `logs/app.log` to see the error.
2. **Corrupt Config**: Delete `config.yaml` and restart to regenerate defaults.
3. **Database Lock**: Delete `.serapeum/serapeum.sqlite3-journal` if it exists (indicates a crash during write).

### 5. Compliance Analysis Returns 0 Results
**Problem**: The compliance report says "No standards found".
**Solution**:
1. **Database Empty**: The standards database might be uninitialized.
2. **Run Seeder**: Run the following command in terminal:
   ```bash
   python -m src.setup.standards_seed --json data/standards.json
   ```
3. **Check Standard Selection**: Ensure you selected the correct standard (e.g., SBC 2018) in the dropdown.

---

## 📞 Getting Help
If you still have issues, please generate a **Diagnostic Report**:
1. Go to **Help > Diagnostics**.
2. Click **"Run Diagnostics"**.
3. Save the report and email it to `support@serapeum.ai`.
