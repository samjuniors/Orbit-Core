# Orbit Core PowerShell CLI launcher (inside the verified Universal Setup ZIP).
# Runs the same Python release-aware CLI as the persistent orbit.cmd launcher.
# No admin privileges, PATH editing, automatic download or host writes here.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $OrbitArguments
)
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'orbit_cli.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    Write-Error 'This launcher must be run from the extracted official Orbit Universal Setup ZIP.'
    exit 1
}
$launcher = Get-Command 'py' -ErrorAction SilentlyContinue
if ($launcher) {
    & py -3 $script @OrbitArguments
} else {
    $python = Get-Command 'python3' -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command 'python' -ErrorAction SilentlyContinue }
    if (-not $python) {
        Write-Error 'Python 3.10-3.13 is required; no compatible Python command found.'
        exit 1
    }
    & $python.Source $script @OrbitArguments
}
exit $LASTEXITCODE
