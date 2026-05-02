param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptRoot "..")

Push-Location $RepoRoot
try {
    & $Python -m demos.iter9_visual_solver.cli.prompted_launcher
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
