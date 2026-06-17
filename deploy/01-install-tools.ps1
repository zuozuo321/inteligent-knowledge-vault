<#
.SYNOPSIS
    安装工具链：Git, ffmpeg, yt-dlp, FastGithub
.DESCRIPTION
    将工具安装到 $ToolsDir 目录，并配置系统 PATH。
    FastGithub 用于加速国内 GitHub 访问。
#>

$ErrorActionPreference = "Stop"
$ToolsDir = "D:\左悦琦\.tools"

# 确保目录存在
if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
}

Write-Host "=== 安装工具链 ===" -ForegroundColor Cyan

# 1. 安装 Git
Write-Host "[1/5] 安装 Git..." -ForegroundColor Yellow
try {
    winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements
    Write-Host "  Git 安装完成" -ForegroundColor Green
} catch {
    Write-Host "  警告：Git 安装失败（$($_.Exception.Message)），请手动安装" -ForegroundColor Red
}

# 2. 安装 ffmpeg
Write-Host "[2/5] 安装 ffmpeg..." -ForegroundColor Yellow
try {
    winget install --id Gyan.FFmpeg -e --source winget --silent --accept-package-agreements --accept-source-agreements
    Write-Host "  ffmpeg 安装完成" -ForegroundColor Green
} catch {
    Write-Host "  警告：ffmpeg 安装失败（$($_.Exception.Message)），请手动安装" -ForegroundColor Red
}

# 3. 安装 yt-dlp
Write-Host "[3/5] 安装 yt-dlp..." -ForegroundColor Yellow
$ytdlpPath = Join-Path $ToolsDir "yt-dlp.exe"
if (-not (Test-Path $ytdlpPath)) {
    try {
        Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile $ytdlpPath
        Write-Host "  yt-dlp 下载完成" -ForegroundColor Green
    } catch {
        Write-Host "  警告：yt-dlp 下载失败（$($_.Exception.Message)）" -ForegroundColor Red
    }
} else {
    Write-Host "  yt-dlp 已存在，跳过" -ForegroundColor Green
}

# 4. 安装 FastGithub（GitHub 加速）
Write-Host "[4/5] 安装 FastGithub..." -ForegroundColor Yellow
$fastDir = Join-Path $ToolsDir "fastgithub"
$fastExe = Join-Path $fastDir "fastgithub.exe"
if (-not (Test-Path $fastExe)) {
    try {
        $zipUrl = "https://gitee.com/XingYuan55/FastGithub/releases/download/2.1.4/fastgithub_win-x64.zip"
        $zipPath = Join-Path $ToolsDir "fastgithub.zip"
        Write-Host "  从 Gitee 镜像下载 FastGithub..."
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -TimeoutSec 120 -UseBasicParsing
        Write-Host "  解压到 $fastDir..."
        Expand-Archive -Path $zipPath -DestinationPath $ToolsDir -Force
        Rename-Item (Join-Path $ToolsDir "fastgithub_win-x64") $fastDir -Force -ErrorAction SilentlyContinue
        Remove-Item $zipPath
        Write-Host "  FastGithub 安装完成" -ForegroundColor Green
    } catch {
        Write-Host "  警告：FastGithub 安装失败（$($_.Exception.Message)），请手动安装" -ForegroundColor Red
    }
} else {
    Write-Host "  FastGithub 已存在，跳过" -ForegroundColor Green
}

# 5. 配置 Git SSL（FastGithub DNS劫持模式下需跳过 github.com 证书验证）
Write-Host "[5/5] 配置 Git..." -ForegroundColor Yellow
$fastRunning = Get-Process -Name "fastgithub" -ErrorAction SilentlyContinue
if ($fastRunning) {
    git config --global http.https://github.com.sslVerify false
    Write-Host "  Git 已配置 github.com SSL 例外（适配 FastGithub DNS 代理）" -ForegroundColor Green
} else {
    Write-Host "  提示：FastGithub 未运行，SSL 配置跳过（启动后执行: git config --global http.https://github.com.sslVerify false）" -ForegroundColor DarkYellow
}

# 6. 配置 PATH
Write-Host "配置 PATH..." -ForegroundColor Yellow
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$ToolsDir*") {
    $newPath = "$ToolsDir;" + $userPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    # 更新当前会话
    $env:Path = $newPath + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
    Write-Host "  PATH 已更新" -ForegroundColor Green
} else {
    Write-Host "  PATH 已包含 $ToolsDir，跳过" -ForegroundColor Green
}

Write-Host "=== 工具链安装完成 ===" -ForegroundColor Cyan