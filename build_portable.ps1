$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "[SerapeumAI] Portable build starting..."
Write-Host "[SerapeumAI] Repo root: $RepoRoot"

$SpecPath = Join-Path $RepoRoot "SerapeumAI_Portable.spec"
if (-not (Test-Path $SpecPath)) {
    Write-Host "[ERROR] Missing packaging spec: $SpecPath"
    exit 1
}

Write-Host "[SerapeumAI] Checking PyInstaller availability..."
$PyInstallerCheck = py -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller is not available in the current Python environment."
    Write-Host "Install it in your build environment, then rerun this script. No dependency install is performed by this script."
    exit 1
}
Write-Host "[SerapeumAI] PyInstaller: $PyInstallerCheck"

Write-Host "[SerapeumAI] Removing old local build outputs..."
if (Test-Path (Join-Path $RepoRoot "build")) { Remove-Item (Join-Path $RepoRoot "build") -Recurse -Force }
if (Test-Path (Join-Path $RepoRoot "dist")) { Remove-Item (Join-Path $RepoRoot "dist") -Recurse -Force }

Write-Host "[SerapeumAI] Running PyInstaller..."
py -m PyInstaller --clean --noconfirm $SpecPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed."
    exit $LASTEXITCODE
}

$ExePath = Join-Path $RepoRoot "dist\SerapeumAI_Portable\SerapeumAI.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "[ERROR] Expected EXE was not produced: $ExePath"
    exit 1
}

Write-Host "[SerapeumAI] Portable build complete."
Write-Host "[SerapeumAI] EXE: $ExePath"
Get-Item $ExePath | Select-Object FullName, Length, LastWriteTime
