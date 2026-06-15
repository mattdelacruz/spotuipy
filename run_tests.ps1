<#
.SYNOPSIS
    Run the spotuipy unit test suite on Windows with labelled sections.

.DESCRIPTION
    Each test file covers one area of the codebase. This script runs them one
    group at a time with a header describing what that group verifies, then
    prints a combined summary at the end.

.EXAMPLE
    .\run_tests.ps1
        Run everything (verbose).

.EXAMPLE
    .\run_tests.ps1 -Quiet
        Run with less per-test output.

.NOTES
    If you get an execution-policy error, either run:
        powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
    or allow local scripts for your user once:
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#>

param(
    [switch]$Quiet
)

# Move to the directory this script lives in, so it works from anywhere.
Set-Location -Path $PSScriptRoot

# pytest verbosity.
$PytestFlags = if ($Quiet) { "-q" } else { "-v" }

# Make sure pytest is available before doing anything else.
& python -m pytest --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "pytest is not installed. Install it with:"
    Write-Host "    pip install pytest"
    exit 1
}

# Each entry: a test file and a human-readable description of what it verifies.
$TestGroups = @(
    @{
        File  = "tests\test_track.py"
        Label = "Track data model - lookups, ordering, and that missing keys return None instead of raising"
    },
    @{
        File  = "tests\test_ended_naturally.py"
        Label = "Natural-end heuristic - distinguishes a track finishing on its own from a manual skip"
    },
    @{
        File  = "tests\test_device_selection.py"
        Label = "Device selection - preference order (spotifyd, then active, then first available)"
    }
)

function Write-Divider {
    Write-Host "------------------------------------------------------------"
}

$OverallStatus = 0

foreach ($group in $TestGroups) {
    Write-Divider
    Write-Host "RUNNING: $($group.File)"
    Write-Host "VERIFIES: $($group.Label)"
    Write-Divider

    & python -m pytest $group.File $PytestFlags
    if ($LASTEXITCODE -ne 0) {
        $OverallStatus = 1
        Write-Host ">>> FAILURES in $($group.File)"
    }
    Write-Host ""
}

# Combined summary across the whole suite.
Write-Divider
Write-Host "COMBINED SUMMARY"
Write-Divider
& python -m pytest tests\ -q

if ($OverallStatus -eq 0) {
    Write-Host ""
    Write-Host "All test groups passed."
}
else {
    Write-Host ""
    Write-Host "One or more test groups had failures (see above)."
}

exit $OverallStatus