# Windows PowerShell Setup Script for AI Generation Platform

Write-Host "🚀 Setting up AI Generation Platform on Windows..." -ForegroundColor Green

# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python is not installed. Please install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Check Python version
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "✅ Python version: $pythonVersion" -ForegroundColor Green

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "⬆️ Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install backend dependencies
Write-Host "📚 Installing backend dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "models\diffusion"
New-Item -ItemType Directory -Force -Path "models\llm"
New-Item -ItemType Directory -Force -Path "models\lora"
New-Item -ItemType Directory -Force -Path "logs"
New-Item -ItemType Directory -Force -Path "uploads"
New-Item -ItemType Directory -Force -Path "outputs"

# Set up environment file
if (-not (Test-Path ".env")) {
    Write-Host "⚙️ Creating .env file..." -ForegroundColor Yellow
    @"
# Environment
ENV=dev
DEBUG=true

# Database (SQLite for local development)
DATABASE_URL=sqlite:///./ai_generation.db
REDIS_URL=redis://localhost:6379

# JWT Secrets (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=your-secret-key-change-this-in-production-$(Get-Random)
ACCESS_TOKEN_SECRET=your-access-token-secret-change-this-$(Get-Random)
REFRESH_TOKEN_SECRET=your-refresh-token-secret-change-this-$(Get-Random)
WORKER_TOKEN_SECRET=your-worker-token-secret-change-this-$(Get-Random)

# Supabase (optional for local development)
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# S3 Storage (optional for local development)
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# Stripe (optional for local development)
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# LLM APIs (optional for local development)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GROQ_API_KEY=your-groq-api-key
TOGETHER_API_KEY=your-together-api-key

# GPU Workers (optional for local development)
VAST_AI_API_KEY=your-vast-ai-api-key
RUNPOD_API_KEY=your-runpod-api-key

# App Configuration
API_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Created .env file with random secrets" -ForegroundColor Green
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Install SQLite support
Write-Host "🗄️ Installing SQLite support..." -ForegroundColor Yellow
pip install sqlite3

Write-Host ""
Write-Host "🎉 Environment setup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start Redis (if you have it installed) or use Docker" -ForegroundColor White
Write-Host "2. Run database migrations: python -m alembic upgrade head" -ForegroundColor White
Write-Host "3. Start the backend: python -m uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "4. Open http://localhost:8000 in your browser" -ForegroundColor White
Write-Host ""
Write-Host "For Redis, you can:" -ForegroundColor Cyan
Write-Host "- Install Redis for Windows" -ForegroundColor White
Write-Host "- Use Docker: docker run -d -p 6379:6379 redis:alpine" -ForegroundColor White
Write-Host "- Or modify .env to use a different Redis URL" -ForegroundColor White
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Green


