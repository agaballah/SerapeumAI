# GenerateBootstrap.ps1
# Called by Start_SerapeumAI_Nara_Developer.cmd at boot time.
# Generates MANAGER_BOOTSTRAP.md -- the single file the Owner pastes into ChatGPT each morning.

$root = "D:\SerapeumAI"
Set-Location $root

$contractFile  = ".ai_developer_control\SerapeumAI_AI_Developer_Contract.md"
$prefsFile     = ".ai_developer_control\USER_PREFERENCES.md"
$stateFile     = ".ai_developer_control\PROJECT_STATE.md"
$taskFile      = ".ai_developer_control\CURRENT_TASK.md"
$decisionsFile = ".ai_developer_control\MANAGER_DECISION_LOG.md"
$queueFile     = ".ai_developer_control\OWNER_APPROVAL_QUEUE.md"
$outputFile    = ".ai_developer_control\MANAGER_BOOTSTRAP.md"

# Read all source files
$contract  = Get-Content $contractFile -Raw -ErrorAction SilentlyContinue
$prefs     = Get-Content $prefsFile    -Raw -ErrorAction SilentlyContinue
$state     = Get-Content $stateFile    -Raw -ErrorAction SilentlyContinue
$task      = Get-Content $taskFile     -Raw -ErrorAction SilentlyContinue
$queue     = Get-Content $queueFile    -Raw -ErrorAction SilentlyContinue

# Get last 50 lines of decision log
$decisions = (Get-Content $decisionsFile -ErrorAction SilentlyContinue | Select-Object -Last 50) -join "`n"

# Extract immutable section from contract
$startMark = "<!-- IMMUTABLE_CONSTITUTION_START -->"
$endMark   = "<!-- IMMUTABLE_CONSTITUTION_END -->"
$s    = $contract.IndexOf($startMark)
$e    = $contract.IndexOf($endMark)
$core = if ($s -ge 0 -and $e -ge 0) {
    $contract.Substring($s, ($e - $s) + $endMark.Length)
} else {
    "[ERROR: IMMUTABLE_CONSTITUTION markers not found in contract]"
}

# Build bootstrap content
$lines = @()
$lines += "# SerapeumAI Manager Bootstrap"
$lines += "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$lines += "# Drop this file in your ChatGPT Manager chat at the start of each session."
$lines += ""
$lines += "---"
$lines += ""
$lines += "## SECTION I -- IMMUTABLE CONSTITUTION"
$lines += ""
$lines += $core
$lines += ""
$lines += "---"
$lines += ""
$lines += "## SECTION II -- USER PREFERENCES"
$lines += ""
$lines += $prefs
$lines += ""
$lines += "---"
$lines += ""
$lines += "## SECTION III -- PROJECT STATE"
$lines += ""
$lines += $state
$lines += ""
$lines += "---"
$lines += ""
$lines += "## CURRENT TASK"
$lines += ""
$lines += $task
$lines += ""
$lines += "---"
$lines += ""
$lines += "## LAST MANAGER DECISIONS"
$lines += ""
$lines += $decisions
$lines += ""
$lines += "---"
$lines += ""
$lines += "## OWNER APPROVAL QUEUE"
$lines += ""
$lines += $queue

# Write output (UTF8 no BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($outputFile, $lines, $utf8NoBom)

Write-Host "BOOTSTRAP_OK: $outputFile"
