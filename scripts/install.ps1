param(
    [string]$Source,
    [switch]$Yes,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error 'Python 3.11+ is required. Install it from https://www.python.org/downloads/ and rerun. No additional interpreter is installed automatically.'
    exit 2
}
$arguments = @((Join-Path $PSScriptRoot 'install.py'))
if ($Source) { $arguments += @('--source', $Source) }
if ($Yes) { $arguments += '--yes' }
if ($DryRun) { $arguments += '--dry-run' }
& $python.Source @arguments
exit $LASTEXITCODE
