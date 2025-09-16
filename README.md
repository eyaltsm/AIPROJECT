## AI Generation Platform - Quickstart

This repo contains:
- Backend API (FastAPI) in `backend/` (Compose runs `backend/working_main.py`)
- GPU Worker in `worker/` (runs SDXL pipelines)
- Cloudflare Tunnel scripts in `scripts/` (expose local backend to the internet)

### 0) Prereqs
- Docker + Docker Compose
- Python 3.11+ for the worker (local runs) and for small utilities

### 1) Boot the backend stack (DB, Redis, MinIO, API)
From repo root:

```bash
docker compose up -d

# (Optional) Run alembic migrations if using the full app wiring
# docker compose exec backend alembic upgrade head
```

Health checks:
- Local health: `http://localhost:8000/api/health`
- Swagger UI (local): `http://localhost:8000/api/docs`

### 2) Start a Cloudflare Tunnel (expose your local API)
Windows PowerShell:
```powershell
Set-Location D:\Aiproject
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_tunnel.ps1
```
The script prints a public URL like:
```
https://<random>.trycloudflare.com
```

Keep this terminal open. You’ll use this URL as `CONTROL_BASE_URL` (+ `/api`).

### 3) Prepare models (only once, if running worker locally)
```powershell
Set-Location D:\Aiproject\worker
python .\download_models.py
```
This creates `worker/models/sdxl-base` (and refiner if not skipped).

### 4) Run the worker (choose one)

#### A) Local worker (CPU or your local GPU)
```powershell
Set-Location D:\Aiproject\worker
$env:CONTROL_BASE_URL = "https://<your-tunnel>.trycloudflare.com/api"
$env:WORKER_TOKEN     = "dev-worker-token"
$env:S3_ENDPOINT_URL  = "http://localhost:9000"
$env:S3_BUCKET        = "ai-generation-dev"
$env:S3_ACCESS_KEY    = "minioadmin"
$env:S3_SECRET_KEY    = "minioadmin123"
python .\executor.py
```

#### B) Vast.ai GPU worker
- In Vast Instance Portal → Terminal:
```bash
git clone <your_repo_url> Aiproject && cd Aiproject/worker
pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu121
pip install --upgrade diffusers transformers accelerate safetensors invisible-watermark boto3 httpx structlog
python download_models.py

export CONTROL_BASE_URL="https://<your-tunnel>.trycloudflare.com/api"
export WORKER_TOKEN="dev-worker-token"
export S3_ENDPOINT_URL="http://<your-s3-endpoint>"
export S3_BUCKET="ai-generation-dev"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin123"
python executor.py
```

Note: On images that use `worker/onstart.sh`, the script downloads models, starts the worker, and runs an idle watchdog. Set `CONTROL_BASE_URL`, `WORKER_TOKEN`, `S3_*`, and optionally `VAST_API_KEY`/`VAST_INSTANCE_ID` envs.

### 5) Submit a generation prompt (Swagger “dashboard”)
Open the tunnel URL + `/api/docs` in your browser, for example:
```
https://<your-tunnel>.trycloudflare.com/api/docs
```

Create a job (txt2img):
1. In Swagger, choose `POST /api/jobs`
2. Example body:
```json
{
  "kind": "generate_image",
  "payload_json": {
    "mode": "txt2img",
    "prompt": "photorealistic portrait, soft daylight",
    "steps": 26,
    "guidance": 6.0,
    "width": 1024,
    "height": 1024,
    "target": "gpu"  
  }
}
```

The worker will claim the job, generate the image, upload to S3/MinIO, and mark it `COMPLETED`.

Retrieve the result:
- `GET /api/jobs/{id}` → read `result_json.object_key` (e.g., `outputs/u123/456.png`)
- Open MinIO console at `http://localhost:9001` → bucket `ai-generation-dev` to download the object.

### 6) Vast.ai autoscaling (on-demand GPU)
We include:
- `backend/app/services/vast_service.py`: start/stop/destroy helpers (uses `VAST_AI_API_KEY`).
- `worker/onstart.sh`: idle watchdog calls `/workers/claim-dryrun?target=gpu`; after `GPU_IDLE_TIMEOUT_SEC` (default 180s) it stops/destroys the instance.

Relevant envs (backend `.env`):
```
VAST_AI_API_KEY=...
VAST_GPU_FILTER=RTX_4090
VAST_IMAGE=
GPU_IDLE_TIMEOUT_SEC=180
STOP_MODE=stop  # or destroy
```

### 7) Troubleshooting
- Invalid host header on tunnel: add your tunnel host to `ALLOWED_HOSTS` (already done in config).
- No jobs claimed: ensure you created a job in Swagger and that `CONTROL_BASE_URL` matches your tunnel (include `/api`).
- S3 upload errors: ensure MinIO bucket `ai-generation-dev` exists and your S3 envs are correct.
- CPU-only: worker uses CPU automatically; it’s slower but OK for a smoke test.

### 8) Where to put your prompt
- In Swagger (`/api/docs`) under `POST /api/jobs`, set `payload_json.prompt`.
- Or call the API directly with the same JSON body.


