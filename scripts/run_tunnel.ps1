param(
  [string]$LocalUrl = "http://localhost:8000"
)

$dl = Join-Path $PSScriptRoot "cloudflared.exe"
if (!(Test-Path $dl)) {
  Write-Host "Downloading cloudflared..."
  Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $dl
}

Write-Host "Starting Cloudflare Tunnel to $LocalUrl ..."
& $dl tunnel --url $LocalUrl


