# SerapeumAI - Automated Windows Setup Script
# This script uses the built-in Windows Package Manager (winget) to silently
# install Python 3.11 and Node.js without requiring the user to do anything.

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       SerapeumAI - Initial System Setup" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/3] Checking for Python 3.11..." -ForegroundColor Yellow

# Check if Python is installed
$pythonCheck = Get-Command "python" -ErrorAction SilentlyContinue
if ($null -eq $pythonCheck) {
    Write-Host "Python not found. Installing Python 3.11 silently... (This may take a minute)" -ForegroundColor Yellow
    # Install Python 3.11 using winget (silent install, adds to PATH automatically)
    winget install --id Python.Python.3.11 --exact --silent --accept-package-agreements --accept-source-agreements
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Python. Please download and install it manually from python.org." -ForegroundColor Red
        Pause
        exit 1
    }
    Write-Host "Python 3.11 installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Python is already installed." -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/3] Checking for Node.js (Required for AI Server CLI)..." -ForegroundColor Yellow

# Check if Node.js (npm) is installed
$npmCheck = Get-Command "npm" -ErrorAction SilentlyContinue
if ($null -eq $npmCheck) {
    Write-Host "Node.js not found. Installing Node.js LTS silently..." -ForegroundColor Yellow
    # Install Node.js using winget
    winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Node.js. Please download and install it manually from nodejs.org." -ForegroundColor Red
        Pause
        exit 1
    }
    Write-Host "Node.js installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Node.js is already installed." -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Updating Environment Variables..." -ForegroundColor Yellow
# Refresh environment variables in the current session so we can use python and npm immediately
try {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} catch {
    Write-Host "Note: Could not fully refresh environment variables. You might need to restart your terminal after setup." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " System Setup Complete! Launching SerapeumAI Installer..." -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Call the original Install.bat to finish the python pip installations
if (Test-Path "Install.bat") {
    Start-Process "cmd.exe" -ArgumentList "/c Install.bat" -Wait
} else {
    Write-Host "[ERROR] Install.bat not found in the current directory." -ForegroundColor Red
}

Write-Host ""
Write-Host "All done! You can now use Start.bat to launch the application." -ForegroundColor Green
Write-Host "The setup window will close when you press any key."
Pause
