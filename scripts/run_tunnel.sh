#!/usr/bin/env bash
set -e
LOCAL_URL="${1:-http://localhost:8000}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared (Linux x86_64) ..."
  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
  chmod +x cloudflared
  sudo mv cloudflared /usr/local/bin/
fi

echo "Starting Cloudflare Tunnel to $LOCAL_URL ..."
cloudflared tunnel --url "$LOCAL_URL"


