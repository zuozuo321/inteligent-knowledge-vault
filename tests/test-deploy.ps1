param([Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference = 'Stop'
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TestRoot = Join-Path ([IO.Path]::GetTempPath()) ('vault-deploy-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $TestRoot | Out-Null
Copy-Item (Join-Path $ProjectRoot 'deploy') $TestRoot -Recurse
New-Item -ItemType Directory -Path (Join-Path $TestRoot 'config') | Out-Null
Copy-Item (Join-Path $ProjectRoot 'config\vault') (Join-Path $TestRoot 'config\vault') -Recurse
New-Item -ItemType Directory -Path (Join-Path $TestRoot 'config\obsidian') | Out-Null
Get-ChildItem (Join-Path $ProjectRoot 'config\obsidian') -File | Copy-Item -Destination (Join-Path $TestRoot 'config\obsidian')
$Vault = Join-Path $TestRoot 'personal vault'
$Script = Join-Path $TestRoot 'deploy\03-configure-claude.ps1'
& $Script -VaultPath $Vault -PythonPath $PythonPath
if (-not (Test-Path (Join-Path $Vault '.obsidian\app.json'))) { throw 'Missing Obsidian config' }
if (-not (Test-Path (Join-Path $Vault 'index\home.md'))) { throw 'Missing homepage' }
Set-Content (Join-Path $Vault 'index\home.md') 'PERSONAL NOTE'
Set-Content (Join-Path $Vault '.obsidian\app.json') '{"userSetting":true}'
$Mcp = Join-Path $TestRoot '.mcp.json'
$config = Get-Content $Mcp -Raw | ConvertFrom-Json
$config.mcpServers | Add-Member -NotePropertyName custom -NotePropertyValue @{command='keep-me'}
$config | ConvertTo-Json -Depth 10 | Set-Content $Mcp
& $Script -VaultPath $Vault -PythonPath $PythonPath
if ((Get-Content (Join-Path $Vault 'index\home.md') -Raw).Trim() -ne 'PERSONAL NOTE') { throw 'Note overwritten' }
if (-not ((Get-Content (Join-Path $Vault '.obsidian\app.json') -Raw | ConvertFrom-Json).userSetting)) { throw 'Settings overwritten' }
$config = Get-Content $Mcp -Raw | ConvertFrom-Json
if ($config.mcpServers.custom.command -ne 'keep-me') { throw 'Other MCP configuration lost' }
if ($config.mcpServers.obsidian.env.VAULT_PATH -ne $Vault) { throw 'Vault path not rendered' }
if ($config.mcpServers.obsidian.command -ne $PythonPath) { throw 'Python path not rendered' }
if (-not (Get-ChildItem $TestRoot -Filter '.mcp.json.backup-*')) { throw 'Backup missing' }
Write-Host 'PASS: initial configuration, idempotence, preservation, rendered paths and backup.'
Write-Host "Test files retained for inspection: $TestRoot"
