<#
.SYNOPSIS
    配置 Claude Code 连接 MCP 服务
.DESCRIPTION
    将 claude-settings.json 模板复制到用户目录，配置 MCP 服务连接
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigDir = Join-Path $ProjectRoot "config"
$SettingsTemplate = Join-Path $ConfigDir "claude-settings.json"
$ClaudeDir = "$env:USERPROFILE\.claude"
$ClaudeSettings = Join-Path $ClaudeDir "settings.json"

Write-Host "=== 配置 Claude Code ===" -ForegroundColor Cyan

# 1. 确保 .claude 目录存在
if (-not (Test-Path $ClaudeDir)) {
    New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null
    Write-Host "  创建 .claude 目录" -ForegroundColor Green
}

# 2. 备份现有配置
if (Test-Path $ClaudeSettings) {
    $backup = "$ClaudeSettings.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $ClaudeSettings $backup
    Write-Host "  已备份现有配置到 $backup" -ForegroundColor Yellow
}

# 3. 复制模板配置
if (Test-Path $SettingsTemplate) {
    Copy-Item $SettingsTemplate $ClaudeSettings -Force
    Write-Host "  配置模板已复制到 $ClaudeSettings" -ForegroundColor Green
    Write-Host "  注意：请编辑该文件，替换占位符 `$VAULT_PATH 为实际路径" -ForegroundColor Yellow
} else {
    Write-Host "  错误：找不到配置模板 $SettingsTemplate" -ForegroundColor Red
    exit 1
}

# 4. 复制 .mcp.json
$McpTemplate = Join-Path $ConfigDir "mcp-template.json"
$McpJson = Join-Path $ProjectRoot ".mcp.json"
if (Test-Path $McpTemplate) {
    Copy-Item $McpTemplate $McpJson -Force
    Write-Host "  .mcp.json 已复制到项目根目录" -ForegroundColor Green
    Write-Host "  注意：请编辑该文件，替换占位符为实际路径" -ForegroundColor Yellow
} else {
    Write-Host "  警告：找不到 .mcp.json 模板" -ForegroundColor Red
}

Write-Host "=== Claude Code 配置完成 ===" -ForegroundColor Cyan

# 5. 配置 Obsidian（社区插件即装即用）
$ObsidianTemplateDir = Join-Path $ConfigDir "obsidian"
if (Test-Path $ObsidianTemplateDir) {
    Write-Host "[5/5] 配置 Obsidian..." -ForegroundColor Yellow

    # 获取知识库路径（优先环境变量，否则交互输入）
    if ($env:VAULT_PATH) {
        $VaultPath = $env:VAULT_PATH
    } elseif ($env:KNOWLEDGE_VAULT_PATH) {
        $VaultPath = $env:KNOWLEDGE_VAULT_PATH
    } else {
        $VaultPath = Read-Host "请输入知识库路径（例如 D:\知识库）"
    }

    if ($VaultPath -and (Test-Path $VaultPath)) {
        $VaultObsidian = Join-Path $VaultPath ".obsidian"

        # 复制 Obsidian 配置文件
        $obsidianFiles = @("community-plugins.json", "core-plugins.json", "app.json", "appearance.json")
        foreach ($f in $obsidianFiles) {
            $src = Join-Path $ObsidianTemplateDir $f
            if (Test-Path $src) {
                Copy-Item $src $VaultObsidian -Force
            }
        }
        Write-Host "  Obsidian 配置文件已复制" -ForegroundColor Green

        # 复制社区插件（含 main.js，无需新用户手动安装）
        $PluginSrc = Join-Path $ObsidianTemplateDir "plugins"
        $PluginDst = Join-Path $VaultObsidian "plugins"
        if (Test-Path $PluginSrc) {
            if (-not (Test-Path $PluginDst)) {
                New-Item -ItemType Directory -Force -Path $PluginDst | Out-Null
            }
            Get-ChildItem -Directory $PluginSrc | ForEach-Object {
                $destDir = Join-Path $PluginDst $_.Name
                Copy-Item $_.FullName $destDir -Recurse -Force
                Write-Host "  插件 $($_.Name) 已安装" -ForegroundColor Green
            }
        }
        Write-Host "  Obsidian 配置完成：新用户打开知识库即可使用，无需去插件市场安装" -ForegroundColor Green
    } else {
        Write-Host "  警告：路径 '$VaultPath' 不存在，跳过 Obsidian 配置" -ForegroundColor Red
        Write-Host "  部署后请手动运行: Copy-Item -Recurse config\obsidian\ <你的知识库路径>\.obsidian\" -ForegroundColor Yellow
    }
} else {
    Write-Host "  警告：仓库中无 config/obsidian/ 配置模板，跳过" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "下一步：运行 04-install-whisper.ps1 安装语音识别模型" -ForegroundColor Magenta