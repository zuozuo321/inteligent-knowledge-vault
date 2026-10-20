param([string]$Model = "tiny")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonPath)) { throw "Run 02-setup-mcp-servers.ps1 first." }
& $PythonPath -m pip install -r (Join-Path $ProjectRoot "requirements-transcription.txt")
if ($LASTEXITCODE -ne 0) { throw "Transcription dependency installation failed." }
& $PythonPath -c "import sys; from faster_whisper import WhisperModel; WhisperModel(sys.argv[1], device='cpu', compute_type='int8')" $Model
if ($LASTEXITCODE -ne 0) { throw "Whisper model download/load failed." }
Write-Host "Whisper ready: $Model"
