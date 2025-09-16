#!/usr/bin/env python3
"""
Database Setup Script for AI Generation Platform
Creates SQLite database and runs migrations
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import engine, Base
from app.models import *  # Import all models
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def setup_database():
    """Set up the database with all tables."""
    try:
        print("🗄️ Setting up database...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully!")
        print("📍 Database file: ai_generation.db")
        print("")
        print("You can now start the backend server:")
        print("  python run_local.py")
        print("")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        logger.error("Database setup failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    setup_database()


