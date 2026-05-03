# Install and Run

SerapeumAI is currently a Windows-first local desktop application.

## Development run

From the repository root:

```powershell
python run.py
```

## Packaged executable

After a successful packaging proof, the portable executable is expected at:

```text
dist\SerapeumAI_Portable\SerapeumAI.exe
```

The current release-candidate artifact recorded in #125 is:

```text
dist\SerapeumAI_Portable\SerapeumAI.exe
size: 110206723 bytes
commit: 51bc3280e1adf9e3cc53859cb2f99bc0b8847548
```

## Runtime expectations

The current mounted runtime path expects a local LM Studio-compatible runtime to be available for model-backed analysis/chat features.

The application should still surface runtime state honestly when the runtime or model is not ready.

## System tools

Some document-processing paths may rely on local system tools such as Tesseract OCR or Poppler/PDF utilities when installed. Missing tools should be treated as local capability limitations rather than silent success.

## What this app is not

SerapeumAI does not provide guaranteed legal, contractual, regulatory, or compliance approval. It provides review assistance with evidence and provenance.
