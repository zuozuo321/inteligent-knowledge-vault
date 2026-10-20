param(
    [string]$VaultPath = $env:VAULT_PATH,
    [string]$PythonPath,
    [switch]$InstallCommunityPlugins
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $VaultPath) { $VaultPath = $env:KNOWLEDGE_VAULT_PATH }
if (-not $VaultPath) { $VaultPath = Join-Path $ProjectRoot "vault" }
$VaultPath = [IO.Path]::GetFullPath($VaultPath)
if (-not $PythonPath) { $PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe" }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Python not found: $PythonPath. Run 02-setup-mcp-servers.ps1 first."
}
function Write-NewFile([string]$Path, [string]$Content) {
    if (-not (Test-Path -LiteralPath $Path)) {
        [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding($false)))
    }
}
foreach ($dir in @("", "index", "wiki", "raw", "raw\web", "raw\notes", "raw\bilibili", "outputs", "templates", "attachments", ".obsidian")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $VaultPath $dir) | Out-Null
}
$Seed = Join-Path $ProjectRoot "config\vault"
Get-ChildItem -LiteralPath $Seed -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($Seed.Length + 1)
    $destination = Join-Path $VaultPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Write-NewFile $destination ([IO.File]::ReadAllText($_.FullName))
}
$ObsidianDir = Join-Path $VaultPath ".obsidian"
foreach ($file in @("app.json", "appearance.json", "core-plugins.json")) {
    Write-NewFile (Join-Path $ObsidianDir $file) ([IO.File]::ReadAllText((Join-Path $ProjectRoot "config\obsidian\$file")))
}
Write-NewFile (Join-Path $ObsidianDir "templates.json") '{"folder":"templates","dateFormat":"YYYY-MM-DD","timeFormat":"HH:mm"}'
if ($InstallCommunityPlugins) {
    $pluginRoot = Join-Path $ProjectRoot "config\obsidian\plugins"
    Get-ChildItem -LiteralPath $pluginRoot -Recurse -File | ForEach-Object {
        $destination = Join-Path $ObsidianDir ("plugins\" + $_.FullName.Substring($pluginRoot.Length + 1))
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        if (-not (Test-Path -LiteralPath $destination)) { Copy-Item -LiteralPath $_.FullName -Destination $destination }
    }
    Write-NewFile (Join-Path $ObsidianDir "community-plugins.json") ([IO.File]::ReadAllText((Join-Path $ProjectRoot "config\obsidian\community-plugins.json")))
}
$mcpPath = Join-Path $ProjectRoot ".mcp.json"
$config = if (Test-Path -LiteralPath $mcpPath) {
    Get-Content -LiteralPath $mcpPath -Raw | ConvertFrom-Json
} else { [pscustomobject]@{} }
if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
}
$servers = @{
    obsidian = @{
        command = $PythonPath
        args = @((Join-Path $ProjectRoot "mcp-servers\obsidian-mcp\server.py"))
        env = @{ VAULT_PATH = $VaultPath }
    }
    bilibili = @{
        command = $PythonPath
        args = @((Join-Path $ProjectRoot "mcp-servers\bilibili-mcp\bilibili_mcp_server.py"))
    }
}
foreach ($name in $servers.Keys) {
    $config.mcpServers | Add-Member -NotePropertyName $name -NotePropertyValue $servers[$name] -Force
}
if (Test-Path -LiteralPath $mcpPath) {
    Copy-Item -LiteralPath $mcpPath -Destination "$mcpPath.backup-$(Get-Date -Format 'yyyyMMddHHmmssfff')"
}
[IO.File]::WriteAllText($mcpPath, ($config | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding($false)))
Write-Host "Vault ready: $VaultPath"
Write-Host "Project MCP configuration: $mcpPath"
Write-Host "Existing global Claude settings and existing notes were preserved."
