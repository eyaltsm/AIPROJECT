#!/bin/bash
# Environment Setup Script for AI Generation Platform

set -e

echo "🚀 Setting up AI Generation Platform environment..."

# Check if Python 3.11+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ $(echo "$PYTHON_VERSION < 3.11" | bc -l) -eq 1 ]]; then
    echo "❌ Python 3.11+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
echo "📚 Installing backend dependencies..."
pip install -r requirements.txt

# Install worker dependencies
echo "🤖 Installing worker dependencies..."
pip install -r workers/requirements-gpu.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p models/diffusion
mkdir -p models/llm
mkdir -p models/lora
mkdir -p logs
mkdir -p uploads
mkdir -p outputs

# Set up environment file
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cat > .env << EOF
# Environment
ENV=dev
DEBUG=true

# Database
DATABASE_URL=postgresql://ai_user:ai_password@localhost:5432/ai_generation_db
REDIS_URL=redis://localhost:6379

# JWT Secrets (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_SECRET=your-access-token-secret-change-this
REFRESH_TOKEN_SECRET=your-refresh-token-secret-change-this
WORKER_TOKEN_SECRET=your-worker-token-secret-change-this

# Supabase (configure these)
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# S3 Storage (configure these)
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# Stripe (configure these)
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# LLM APIs (configure these)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GROQ_API_KEY=your-groq-api-key
TOGETHER_API_KEY=your-together-api-key

# GPU Workers (configure these)
VAST_AI_API_KEY=your-vast-ai-api-key
RUNPOD_API_KEY=your-runpod-api-key

# App Configuration
API_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1
EOF
    echo "✅ Created .env file. Please configure the values before running the application."
else
    echo "✅ .env file already exists"
fi

# Initialize Alembic
echo "🗄️ Setting up database migrations..."
if [ ! -d "alembic/versions" ]; then
    alembic init alembic
    echo "✅ Alembic initialized"
else
    echo "✅ Alembic already initialized"
fi

# Create initial migration if it doesn't exist
if [ ! -f "alembic/versions/0001_initial_migration.py" ]; then
    echo "📝 Creating initial migration..."
    alembic revision --autogenerate -m "Initial migration with all tables and indexes"
    echo "✅ Initial migration created"
else
    echo "✅ Initial migration already exists"
fi

echo ""
echo "🎉 Environment setup completed!"
echo ""
echo "Next steps:"
echo "1. Configure your .env file with actual API keys and credentials"
echo "2. Start PostgreSQL and Redis (or use Docker Compose)"
echo "3. Run database migrations: alembic upgrade head"
echo "4. Start the backend: python -m uvicorn app.main:app --reload"
echo "5. Download AI models: python scripts/setup_models.py --info"
echo ""
echo "For GPU workers, you'll need:"
echo "- NVIDIA GPU with CUDA support"
echo "- Docker with GPU support"
echo "- Vast.ai or RunPod API keys"
echo ""
echo "Happy coding! 🚀"


