#!/bin/bash
# GPU Worker Setup Script
# This script runs on GPU instances (Vast.ai, RunPod, etc.)

set -e

echo "🚀 Setting up AI Generation Platform GPU Worker..."

# Update system
apt-get update
apt-get install -y wget curl git python3-pip python3-venv

# Create virtual environment
python3 -m venv /opt/ai-worker
source /opt/ai-worker/bin/activate

# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install core AI libraries
pip install diffusers transformers accelerate
pip install xformers  # For memory efficiency
pip install safetensors
pip install bitsandbytes  # For quantization

# Install LoRA training dependencies
pip install kohya-ss
pip install peft
pip install datasets

# Install ComfyUI dependencies
cd /opt
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Install additional ComfyUI nodes
cd custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
cd ComfyUI-Manager
pip install -r requirements.txt

# Install AnimateDiff for video generation
cd /opt
git clone https://github.com/guoyww/AnimateDiff.git
cd AnimateDiff
pip install -r requirements.txt

# Install worker dependencies
pip install requests
pip install aiohttp
pip install redis
pip install boto3
pip install pillow
pip install opencv-python

# Create worker directory
mkdir -p /opt/ai-worker/worker
cd /opt/ai-worker/worker

# Download worker script
curl -o worker.py https://raw.githubusercontent.com/your-repo/ai-generation-platform/main/backend/workers/worker.py
curl -o model_downloader.py https://raw.githubusercontent.com/your-repo/ai-generation-platform/main/backend/workers/model_downloader.py

# Make scripts executable
chmod +x worker.py model_downloader.py

echo "✅ GPU Worker setup complete!"
echo "Starting worker..."

# Start the worker
python worker.py --api-url $API_BASE_URL --token $WORKER_TOKEN


