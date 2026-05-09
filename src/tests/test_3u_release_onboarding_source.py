from pathlib import Path


def test_pdf_dependency_warning_gives_actionable_windows_steps():
    source = Path("run.py").read_text(encoding="utf-8")
    assert "PDF Tools Setup Required" in source
    assert "Tesseract OCR: needed for scanned-PDF OCR" in source
    assert "Poppler for Windows: needed for PDF page rendering" in source
    assert "pdfinfo.exe" in source
    assert "SerapeumAI did not change your system" in source


def test_project_opening_explains_folder_workspace_model():
    source = Path("src/ui/main_window.py").read_text(encoding="utf-8")
    assert "Open Project Folder" in source
    assert "Choose a folder that contains the project documents" in source
    assert "not a one-file viewer" in source
    assert "Select SerapeumAI Project Folder" in source


def test_runtime_manager_distinguishes_detected_selected_and_recommended_models():
    source = Path("src/ui/dialogs/runtime_manager_dialog.py").read_text(encoding="utf-8")
    assert "Detected/listed model = model found locally" in source
    assert "Selected model = model SerapeumAI is configured to use" in source
    assert "Recommended model = advisory guidance" in source
    assert "not a forced download" in source
    assert "does not start providers, download, load, or unload models" in source
