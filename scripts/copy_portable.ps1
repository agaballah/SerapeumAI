<#
.SYNOPSIS
Copies the built SerapeumAI Portable release artifact to a target directory.

.DESCRIPTION
This script copies the portable release build output (dist/SerapeumAI_Portable)
to a specified destination directory for testing or distribution staging.

.PARAMETER SourcePath
Path to the source portable build directory. Defaults to ./dist/SerapeumAI_Portable relative to script location.

.PARAMETER DestinationPath
Target directory for the copied portable build. Required.

.PARAMETER Force
Overwrite destination if it exists. Default: true.

.PARAMETER ShowDetails
Enable detailed file listing output. Default: false.

.EXAMPLE
.\scripts\copy_portable.ps1 -DestinationPath "C:\Temp\SerapeumAI_Test"

.EXAMPLE
.\scripts\copy_portable.ps1 -SourcePath ".\dist\SerapeumAI_Portable" -DestinationPath "C:\Release\SerapeumAI_v0.3" -ShowDetails
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$SourcePath = (Join-Path (Split-Path $PSScriptRoot -Parent) "dist\SerapeumAI_Portable"),

    [Parameter(Mandatory=$true)]
    [string]$DestinationPath,

    [Parameter(Mandatory=$false)]
    [switch]$Force = $true,

    [Parameter(Mandatory=$false)]
    [switch]$ShowDetails
)

# Ensure source exists
if (-not (Test-Path $SourcePath)) {
    Write-Error "Source path does not exist: $SourcePath"
    exit 1
}

# Ensure destination parent exists
$destParent = Split-Path $DestinationPath -Parent
if (-not (Test-Path $destParent)) {
    try {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    } catch {
        Write-Error "Failed to create destination parent directory: $destParent"
        exit 1
    }
}

# Handle existing destination
if (Test-Path $DestinationPath) {
    if ($Force) {
        Write-Verbose "Removing existing destination: $DestinationPath"
        try {
            Remove-Item $DestinationPath -Recurse -Force -ErrorAction Stop
        } catch {
            Write-Error "Failed to remove existing destination: $_"
            exit 1
        }
    } else {
        Write-Error "Destination already exists and -Force not specified: $DestinationPath"
        exit 1
    }
}

# Perform copy
Write-Host "Copying from: $SourcePath"
Write-Host "Copying to:   $DestinationPath"

try {
    Copy-Item $SourcePath $DestinationPath -Recurse -Force -ErrorAction Stop
} catch {
    Write-Error "Copy failed: $_"
    exit 1
}

# Verify copy
$fileCount = (Get-ChildItem $DestinationPath -Recurse -File | Measure-Object).Count
$totalSize = (Get-ChildItem $DestinationPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)

Write-Host "Copy completed successfully."
Write-Host "Files copied: $fileCount"
Write-Host "Total size:   $totalSizeMB MB"

if ($ShowDetails) {
    Get-ChildItem $DestinationPath -Recurse -File | Select-Object Name, @{Name="Size(MB)";Expression={[math]::Round($_.Length/1MB,2)}}, Directory | Sort-Object Directory, Name | Format-Table -AutoSize
}

exit 0