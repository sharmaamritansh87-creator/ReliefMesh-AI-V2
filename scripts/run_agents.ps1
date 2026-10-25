# Run from the repo root:  .\scripts\run_agents.ps1
$py = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "No .venv found. Create it with:  py -3.12 -m venv .venv" -ForegroundColor Red; exit 1
}
$ver = & $py -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -ge [version]"3.14") {
  Write-Host "The .venv uses Python $ver. uagents needs 3.10-3.13. Recreate it with:  py -3.12 -m venv .venv" -ForegroundColor Red; exit 1
}
Write-Host "Using Python $ver from .venv" -ForegroundColor Green
$env:COORDINATOR_MAILBOX = "1"
foreach ($a in "intake","verification","resource","routing") {
  Start-Process powershell -ArgumentList "-NoExit","-Command","& '$py' -m backend.agents.${a}_agent"
}
Start-Sleep -Seconds 5
& $py -m backend.agents.coordinator_agent