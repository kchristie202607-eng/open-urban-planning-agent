param(
    [string]$Project = "examples\demo_project.json",
    [string]$Output = "output\demo",
    [switch]$RebuildKnowledge
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = "C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$node = "C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$bundledModules = "C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"

Set-Location $projectRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = (Resolve-Path ".deps").Path

if (-not (Test-Path -LiteralPath "node_modules")) {
    New-Item -ItemType Junction -Path "node_modules" -Target $bundledModules | Out-Null
}

if ($RebuildKnowledge) {
    & $python "src\build_kb.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $python "src\kb_index.py" build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python "src\run_workflow.py" $Project --output $Output
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python "scripts\build_deliverables.py" --output $Output
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $node "scripts\build_workbook.mjs" $Output
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m unittest discover -s tests -v
exit $LASTEXITCODE

