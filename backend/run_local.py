#!/usr/bin/env python3
"""
Local Development Runner for AI Generation Platform
Simplified version for local testing
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

def main():
    """Run the FastAPI application locally."""
    print("🚀 Starting AI Generation Platform locally...")
    print("📍 Backend will be available at: http://localhost:8000")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000/health")
    print("")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Set environment variables for local development
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("DEBUG", "true")
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()


