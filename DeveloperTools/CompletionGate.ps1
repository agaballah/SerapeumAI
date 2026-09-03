param(
    [string]$SessionID
)

$root = "D:\SerapeumAI"
Set-Location $root

Write-Host "============================================================"
Write-Host " SerapeumAI -- 5-Gate Completion Check"
Write-Host "============================================================"

if (-not $SessionID) { $SessionID = Get-Date -Format "yyyyMMdd_HHmmss" }

$logFolder = ".ai_developer_control\session_logs"
New-Item -ItemType Directory -Force $logFolder | Out-Null

$techReport    = "$logFolder\${SessionID}_developer_audit.md"
$managerReport = "$logFolder\${SessionID}_manager_summary.md"

$gates   = [ordered]@{}
$results = [ordered]@{}

# GATE 1 -- Task Authorization
$taskFile = ".ai_developer_control\CURRENT_TASK.md"
if ((Test-Path $taskFile) -and (Select-String -Path $taskFile -Pattern "STATUS: APPROVED" -Quiet)) {
    $gates["Gate1_Authorization"] = "PASS"
    $approvedFiles = (Get-Content $taskFile |
        Where-Object { $_ -match "^\s*- " } |
        ForEach-Object { $_.Trim().TrimStart("- ") })
} else {
    $gates["Gate1_Authorization"] = "FAIL - CURRENT_TASK.md missing or STATUS not APPROVED"
    $approvedFiles = @()
}

# GATE 2 -- File Scope
$changedFiles = @(git diff --name-only HEAD 2>$null)
$outOfScope = @()
if ($approvedFiles.Count -gt 0) {
    foreach ($f in $changedFiles) {
        $matched = $false
        foreach ($approved in $approvedFiles) {
            if ($f -like $approved -or $approved -match "none") {
                $matched = $true
                break
            }
        }
        if (-not $matched) { $outOfScope += $f }
    }
    if ($outOfScope.Count -eq 0) {
        $gates["Gate2_FileScope"] = "PASS"
    } else {
        $gates["Gate2_FileScope"] = "FAIL - Unapproved files modified: " + ($outOfScope -join ", ")
    }
} else {
    $gates["Gate2_FileScope"] = "SKIP - No approved files listed (infrastructure task)"
}

# GATE 3 -- Test Verification
$testFile = ".ai_developer_control\TEST_RESULT.md"
if ((Test-Path $testFile) -and (Select-String -Path $testFile -Pattern "RESULT: PASS" -Quiet)) {
    $gates["Gate3_Tests"] = "PASS"
} elseif ((Test-Path $testFile) -and (Select-String -Path $testFile -Pattern "RESULT: FAIL" -Quiet)) {
    $gates["Gate3_Tests"] = "FAIL - TEST_RESULT.md reports FAIL"
} else {
    $gates["Gate3_Tests"] = "FAIL - TEST_RESULT.md missing or no RESULT line found"
}

# GATE 4 -- Development Log
$devlog = ".ai_developer_control\DEVELOPMENT_LOG.md"
if (Test-Path $devlog) {
    $modified = (Get-Item $devlog).LastWriteTime
    if ($modified -gt (Get-Date).AddHours(-2)) {
        $gates["Gate4_Log"] = "PASS"
    } else {
        $gates["Gate4_Log"] = "FAIL - DEVELOPMENT_LOG.md not updated in last 2 hours"
    }
} else {
    $gates["Gate4_Log"] = "FAIL - DEVELOPMENT_LOG.md missing"
}

# GATE 5 -- Governance Hash
$hashFile = ".ai_developer_control\CONTRACT_CORE_HASH.txt"
if (Test-Path $hashFile) {
    $contract = Get-Content ".ai_developer_control\SerapeumAI_AI_Developer_Contract.md" -Raw
    $startMark = "<!-- IMMUTABLE_CONSTITUTION_START -->"
    $endMark   = "<!-- IMMUTABLE_CONSTITUTION_END -->"
    $s = $contract.IndexOf($startMark)
    $e = $contract.IndexOf($endMark)
    if ($s -ge 0 -and $e -ge 0) {
        $section = $contract.Substring($s, ($e - $s) + $endMark.Length)
        $section = $section.Replace("`r", "")
        $bytes   = [System.Text.Encoding]::UTF8.GetBytes($section)
        $sha     = [System.Security.Cryptography.SHA256]::Create()
        $hash    = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
        $stored  = [System.IO.File]::ReadAllLines($hashFile) |
                       Where-Object { $_.Trim() -match "^[a-f0-9]{64}$" } |
                       Select-Object -First 1
        if ($hash -eq $stored) {
            $gates["Gate5_Governance"] = "PASS"
        } else {
            $gates["Gate5_Governance"] = "FAIL - Constitution hash mismatch. Section I may have been tampered."
        }
    } else {
        $gates["Gate5_Governance"] = "FAIL - IMMUTABLE_CONSTITUTION markers missing from contract"
    }
} else {
    $gates["Gate5_Governance"] = "FAIL - CONTRACT_CORE_HASH.txt missing"
}

# Overall result
$failCount = ($gates.Values | Where-Object { $_ -like "FAIL*" }).Count
$overallPass = ($failCount -eq 0)
$overallLabel = if ($overallPass) { "PASS" } else { "FAIL" }

# Write developer audit report
$techLines = @()
$techLines += "# SerapeumAI Developer Session Audit"
$techLines += ""
$techLines += "Session   : $SessionID"
$techLines += "Date      : $(Get-Date)"
$techLines += "Overall   : $overallLabel"
$techLines += ""
$techLines += "---"
$techLines += ""
$techLines += "## Gate Results"
$techLines += ""
foreach ($g in $gates.GetEnumerator()) {
    $techLines += ("- " + $g.Key + ": " + $g.Value)
}
$techLines += ""
$techLines += "---"
$techLines += ""
$techLines += "## Approved Files (from CURRENT_TASK.md)"
$techLines += ($approvedFiles -join "`n")
$techLines += ""
$techLines += "## Changed Files"
$techLines += ($changedFiles -join "`n")
$techLines += ""
$techLines += "## Out-of-Scope Files"
if ($outOfScope.Count -gt 0) {
    $techLines += ($outOfScope -join "`n")
} else {
    $techLines += "None"
}
$techLines += ""
$techLines += "## Git Status"
$techLines += (git status --short)
$techLines += ""
$techLines += "## Git Diff Stat"
$techLines += (git diff --stat HEAD)
$techLines | Out-File $techReport -Encoding UTF8

# Write manager summary report
$taskTitle  = (Get-Content $taskFile -ErrorAction SilentlyContinue | Where-Object { $_ -match "TASK_TITLE:" } | Select-Object -First 1)
$testNotes  = (Get-Content ".ai_developer_control\TEST_RESULT.md" -ErrorAction SilentlyContinue | Where-Object { $_ -match "NOTES:" } | Select-Object -First 1)

if ($outOfScope.Count -gt 0) { $risk = "HIGH - out-of-scope files modified" }
elseif (-not $overallPass)   { $risk = "MEDIUM - gate failure" }
else                          { $risk = "LOW" }

if ($overallPass) {
    $decisionNeeded = "None. Session completed cleanly. Update PROJECT_STATE.md and issue next task."
    $ownerAction    = "None required."
} else {
    $failedList = ($gates.GetEnumerator() | Where-Object { $_.Value -like "FAIL*" } | ForEach-Object { "  - " + $_.Key + ": " + $_.Value }) -join "`n"
    $decisionNeeded = "Session did NOT pass all gates.`nFailed gates:`n$failedList"
    $ownerAction    = "Review failed gates. Instruct Manager to investigate before marking task complete."
}

$manLines = @()
$manLines += "# Manager Summary -- Session $SessionID"
$manLines += ""
$manLines += "Date      : $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$manLines += "Task      : $taskTitle"
$manLines += "Completed : $(if ($overallPass) { 'YES' } else { 'NO' })"
$manLines += "Risk      : $risk"
$manLines += ""
$manLines += "---"
$manLines += ""
$manLines += "## Decision Needed"
$manLines += $decisionNeeded
$manLines += ""
$manLines += "## Owner Action"
$manLines += $ownerAction
$manLines += ""
$manLines += "## Test Notes"
$manLines += $testNotes
$manLines | Out-File $managerReport -Encoding UTF8

# Console output
Write-Host ""
Write-Host "============================================================"
foreach ($g in $gates.GetEnumerator()) {
    $icon = if ($g.Value -like "PASS*" -or $g.Value -like "SKIP*") { "[OK]" } else { "[!!]" }
    Write-Host "$icon  $($g.Key): $($g.Value)"
}
Write-Host "============================================================"
Write-Host "Overall: $overallLabel"
Write-Host ""
Write-Host "Developer audit : $techReport"
Write-Host "Manager summary : $managerReport"
Write-Host "============================================================"

if (-not $overallPass) { exit 1 }
