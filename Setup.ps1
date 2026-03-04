# SerapeumAI - Automated Windows Setup Script
# This script uses the built-in Windows Package Manager (winget) to silently
# install all required system tools for SerapeumAI.

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       SerapeumAI - Initial System Setup" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python 3.11
Write-Host "[1/5] Checking for Python 3.11..." -ForegroundColor Yellow
$pythonCheck = Get-Command "python" -ErrorAction SilentlyContinue
if ($null -eq $pythonCheck) {
    Write-Host "Python not found. Installing Python 3.11 silently..." -ForegroundColor Yellow
    winget install --id Python.Python.3.11 --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Python. Please install manually from python.org" -ForegroundColor Red
        Pause; exit 1
    }
    Write-Host "Python 3.11 installed!" -ForegroundColor Green
} else {
    Write-Host "Python is already installed." -ForegroundColor Green
}

# 2. Node.js (for lms CLI)
Write-Host ""
Write-Host "[2/5] Checking for Node.js (Required for AI Server)..." -ForegroundColor Yellow
$npmCheck = Get-Command "npm" -ErrorAction SilentlyContinue
if ($null -eq $npmCheck) {
    Write-Host "Node.js not found. Installing Node.js LTS silently..." -ForegroundColor Yellow
    winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Node.js. Please install manually from nodejs.org" -ForegroundColor Red
        Pause; exit 1
    }
    Write-Host "Node.js installed!" -ForegroundColor Green
} else {
    Write-Host "Node.js is already installed." -ForegroundColor Green
}

# 3. Tesseract OCR
Write-Host ""
Write-Host "[3/5] Checking for Tesseract OCR (Required for scanned PDFs)..." -ForegroundColor Yellow
$tessCheck = Get-Command "tesseract" -ErrorAction SilentlyContinue
if ($null -eq $tessCheck) {
    Write-Host "Tesseract not found. Installing via winget..." -ForegroundColor Yellow
    winget install --id UB-Mannheim.Tesseract --exact --silent --accept-package-agreements --accept-source-agreements
    Write-Host "Tesseract installed!" -ForegroundColor Green
} else {
    Write-Host "Tesseract is already installed." -ForegroundColor Green
}

# 4. Optional Model Download
Write-Host ""
Write-Host "[4/5] Optional: Download AI Models (~8GB total)" -ForegroundColor Yellow
Write-Host "SerapeumAI uses local AI models to keep your data private." -ForegroundColor White
$choice = Read-Host "Would you like to download the recommended models now? (y/n)"
if ($choice -eq 'y') {
    Write-Host "Initializing AI Server..." -ForegroundColor Yellow
    # Ensure npm finishes installing lms if it's fresh
    Start-Process "cmd.exe" -ArgumentList "/c npm install -g @lmstudio/lms" -Wait
    
    Write-Host "Downloading Reasoning Model (Qwen2.5 VL)..." -ForegroundColor Yellow
    lms get qwen/qwen2.5-vl-7b
    Write-Host "Downloading Vision Model (Llama-3.2 Vision)..." -ForegroundColor Yellow
    lms get leafspark/Llama-3.2-11B-Vision-Instruct-GGUF
    Write-Host "Models downloaded!" -ForegroundColor Green
} else {
    Write-Host "Skipping model download. You can download them later via Start.bat." -ForegroundColor Gray
}

# 5. Refresh Environment Variables
Write-Host ""
Write-Host "[5/5] Finalizing Environment..." -ForegroundColor Yellow
try {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} catch {
    Write-Host "Note: Restart your computer if tools like 'python' or 'lms' are not found after setup." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " System Setup Complete! Launching Python Installer..." -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "Install.bat") {
    Start-Process "cmd.exe" -ArgumentList "/c Install.bat" -Wait
}

Write-Host ""
Write-Host "All done! You can now use Start.bat to launch SerapeumAI." -ForegroundColor Green
Pause
