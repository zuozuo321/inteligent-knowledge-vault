param([switch]$WithTranscription)
$ErrorActionPreference = "Stop"
$packages = @{ git = "Git.Git" }
if ($WithTranscription) { $packages["ffmpeg"] = "Gyan.FFmpeg" }
foreach ($command in $packages.Keys) {
    if (Get-Command $command -ErrorAction SilentlyContinue) { continue }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Install $command and add it to PATH, then retry."
    }
    & winget install --id $packages[$command] -e --source winget --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Failed to install $command." }
}
# Never disable TLS verification or install a network interception service.
