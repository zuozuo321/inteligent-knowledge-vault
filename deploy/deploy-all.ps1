param(
    [string]$VaultPath = $env:VAULT_PATH,
    [string]$PythonPath = "python",
    [switch]$WithTranscription,
    [switch]$InstallCommunityPlugins
)
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "01-install-tools.ps1") -WithTranscription:$WithTranscription
& (Join-Path $PSScriptRoot "02-setup-mcp-servers.ps1") -PythonPath $PythonPath -WithTranscription:$WithTranscription
& (Join-Path $PSScriptRoot "03-configure-claude.ps1") -VaultPath $VaultPath -InstallCommunityPlugins:$InstallCommunityPlugins
if ($WithTranscription) { & (Join-Path $PSScriptRoot "04-install-whisper.ps1") }
Write-Host "Deployment completed. Open the vault in Obsidian and index/home.md to get started."
