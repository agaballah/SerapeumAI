# VerifyHash.ps1
# Called by Start_SerapeumAI_Nara_Developer.cmd to verify the immutable constitution hash.
# Exit 0 = hash matches (OK). Exit 1 = hash mismatch or error (abort).

param(
    [string]$ContractFile  = ".ai_developer_control\SerapeumAI_AI_Developer_Contract.md",
    [string]$HashFile      = ".ai_developer_control\CONTRACT_CORE_HASH.txt"
)

$startMark = "<!-- IMMUTABLE_CONSTITUTION_START -->"
$endMark   = "<!-- IMMUTABLE_CONSTITUTION_END -->"

# --- Read contract ---
if (-not (Test-Path $ContractFile)) {
    Write-Host "HASH_FAIL: contract file not found"
    exit 1
}
$contract = Get-Content $ContractFile -Raw

# --- Find markers ---
$s = $contract.IndexOf($startMark)
$e = $contract.IndexOf($endMark)
if ($s -lt 0 -or $e -lt 0) {
    Write-Host "HASH_FAIL: markers missing"
    exit 1
}

# --- Extract and normalise section ---
$section = $contract.Substring($s, ($e - $s) + $endMark.Length)
$section = $section.Replace("`r", "")

# --- Compute live hash ---
$bytes   = [System.Text.Encoding]::UTF8.GetBytes($section)
$sha     = [System.Security.Cryptography.SHA256]::Create()
$live    = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""

# --- Read stored hash ---
if (-not (Test-Path $HashFile)) {
    Write-Host "HASH_FAIL: hash file not found"
    exit 1
}
$stored = [System.IO.File]::ReadAllLines($HashFile) |
              Where-Object { $_.Trim() -match "^[a-f0-9]{64}$" } |
              Select-Object -First 1

if (-not $stored) {
    Write-Host "HASH_FAIL: no valid hash found in hash file"
    exit 1
}

# --- Compare ---
if ($live -eq $stored) {
    Write-Host "HASH_OK"
    exit 0
} else {
    Write-Host "HASH_FAIL: constitution tampered"
    exit 1
}
