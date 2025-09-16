#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "Starting GPU worker setup..."

apt-get update && apt-get install -y git wget curl python3-pip

cd /workspace
pip install --upgrade pip
pip install -r requirements-worker.txt || true

echo "Ensuring models..."
python download_models.py || true

echo "Launching executor..."
python executor.py &
WORKER_PID=$!

# Idle watchdog for autoscale down
: "${CONTROL_BASE_URL:?need CONTROL_BASE_URL}"
: "${WORKER_TOKEN:?need WORKER_TOKEN}"
: "${GPU_IDLE_TIMEOUT_SEC:=180}"
: "${STOP_MODE:=stop}"
: "${VAST_API_KEY:=}"
: "${VAST_INSTANCE_ID:=}"

IDLE=0
while true; do
  sleep 5
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${WORKER_TOKEN}" "${CONTROL_BASE_URL%/}/workers/claim-dryrun?target=gpu" || echo 000)
  if [ "$CODE" = "204" ]; then
    IDLE=$((IDLE+5))
  else
    IDLE=0
  fi
  if [ $IDLE -ge $GPU_IDLE_TIMEOUT_SEC ]; then
    echo "Idle ${IDLE}s >= ${GPU_IDLE_TIMEOUT_SEC}s. Shutting down Vast instance (${STOP_MODE})."
    if [ -n "$VAST_API_KEY" ] && [ -n "$VAST_INSTANCE_ID" ]; then
      python - <<'PY'
import os, httpx
API=os.environ.get('VAST_API_BASE','https://api.vast.ai')
H={'Authorization':f"Bearer {os.environ['VAST_API_KEY']}"}
i=os.environ.get('VAST_INSTANCE_ID')
if i:
    if (os.environ.get('STOP_MODE','stop').lower()=='destroy'):
        httpx.delete(f"{API}/v0/instances/{i}", headers=H, timeout=30)
    else:
        httpx.post(f"{API}/v0/instances/{i}/stop", headers=H, timeout=30)
PY
    fi
    break
  fi
done

wait $WORKER_PID || true
