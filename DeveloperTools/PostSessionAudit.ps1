param(
    [string]$SessionID
)

$root = "D:\SerapeumAI"
Set-Location $root

Write-Host "============================================================"
Write-Host " SerapeumAI -- Post Session Audit"
Write-Host "============================================================"

if (-not $SessionID) { $SessionID = Get-Date -Format "yyyyMMdd_HHmmss" }

$logFolder = ".ai_developer_control\session_logs"
New-Item -ItemType Directory -Force $logFolder | Out-Null

$report = "$logFolder\${SessionID}_audit_report.md"

# Gather data
$gitStatus    = @(git status --short)
$changedFiles = @(git diff --name-only HEAD 2>$null)
$diffStat     = @(git diff --stat HEAD 2>$null)

# Approved scope from task file
$taskFile      = ".ai_developer_control\CURRENT_TASK.md"
$approvedFiles = @(Get-Content $taskFile -ErrorAction SilentlyContinue |
    Where-Object { $_ -match "^\s*- " } |
    ForEach-Object { $_.Trim().TrimStart("- ") })

# Scope violation check
$outOfScope = @()
if ($approvedFiles.Count -gt 0 -and $changedFiles.Count -gt 0) {
    foreach ($f in $changedFiles) {
        $matched = $false
        foreach ($approved in $approvedFiles) {
            if ($f -like $approved -or $approved -match "none") { $matched = $true; break }
        }
        if (-not $matched) { $outOfScope += $f }
    }
}

# Log freshness
$devlog   = ".ai_developer_control\DEVELOPMENT_LOG.md"
$logFresh = (Test-Path $devlog) -and ((Get-Item $devlog).LastWriteTime -gt (Get-Date).AddHours(-2))

# Test evidence -- read TEST_RESULT.md
$testFile   = ".ai_developer_control\TEST_RESULT.md"
$testResult = if (Test-Path $testFile) { Get-Content $testFile -Raw } else { "NOT FOUND" }
$testPass   = ($testResult -match "RESULT: PASS")

# Scope result label
$scopeLabel = if ($outOfScope.Count -eq 0) { "PASS" } else { "FAIL" }
$testLabel  = if ($testPass) { "PASS" } else { "FAIL or missing" }

# Risk assessment
if ($outOfScope.Count -gt 0) {
    $risk = "HIGH - out-of-scope files: " + ($outOfScope -join ", ")
} elseif (-not $testPass) {
    $risk = "MEDIUM - no passing test evidence"
} elseif (-not $logFresh) {
    $risk = "LOW - log not updated"
} else {
    $risk = "LOW - all checks passed"
}

$decisionNeeded = if ($outOfScope.Count -gt 0 -or -not $testPass) {
    "YES - review failures before marking task complete"
} else {
    "NO - session can be closed"
}

# Build report lines
$lines = @()
$lines += "# SerapeumAI Post Session Audit"
$lines += ""
$lines += "Session : $SessionID"
$lines += "Date    : $(Get-Date)"
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 1. Git Status"
$lines += ""
$lines += ($gitStatus -join "`n")
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 2. Changed Files"
$lines += ""
$lines += ($changedFiles -join "`n")
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 3. Diff Summary"
$lines += ""
$lines += ($diffStat -join "`n")
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 4. Scope Enforcement"
$lines += ""
$lines += "Approved files (from CURRENT_TASK.md):"
$lines += ($approvedFiles -join "`n")
$lines += ""
$lines += "Out-of-scope modifications:"
if ($outOfScope.Count -gt 0) {
    $lines += ($outOfScope -join "`n")
} else {
    $lines += "None -- scope respected."
}
$lines += ""
$lines += "Scope result: $scopeLabel"
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 5. Test Evidence (TEST_RESULT.md)"
$lines += ""
$lines += $testResult
$lines += ""
$lines += "Test result: $testLabel"
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 6. Development Log"
$lines += ""
$lines += "Log updated in last 2 hours: $logFresh"
$lines += ""
$lines += "---"
$lines += ""
$lines += "## 7. Manager Summary"
$lines += ""
$lines += "| Check | Result |"
$lines += "|-------|--------|"
$lines += "| Changed files in scope | $scopeLabel |"
$lines += "| Test evidence present   | $testLabel |"
$lines += "| Development log updated | $logFresh |"
$lines += ""
$lines += "Risk: $risk"
$lines += ""
$lines += "Decision needed: $decisionNeeded"
$lines += ""
$lines += "---"
$lines += ""
$lines += "## End Audit"

$lines | Out-File $report -Encoding UTF8

# Console output
Write-Host ""
Write-Host "Scope violations : $(if ($outOfScope.Count -gt 0) { 'YES - ' + ($outOfScope -join ', ') } else { 'None' })"
Write-Host "Test evidence    : $testLabel"
Write-Host "Log updated      : $logFresh"
Write-Host ""
Write-Host "Audit report: $report"
Write-Host "============================================================"
