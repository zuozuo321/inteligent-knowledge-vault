param([string]$PythonPath = "python", [switch]$WithTranscription)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    & $PythonPath -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Python virtual environment." }
}
$requirements = if ($WithTranscription) { "requirements-transcription.txt" } else { "requirements.txt" }
& $VenvPython -m pip install -r (Join-Path $ProjectRoot $requirements)
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& $VenvPython -c "import mcp, httpx, yaml"
if ($LASTEXITCODE -ne 0) { throw "Dependency verification failed." }
Write-Host "MCP dependencies ready: $VenvPython"
