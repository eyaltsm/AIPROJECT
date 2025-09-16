#!/usr/bin/env python3
"""
Model Setup Script for AI Generation Platform
Downloads and sets up all required AI models
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from workers.model_downloader import ModelDownloader
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


async def setup_models(models_dir: str, include_llm: bool = True, include_lora: bool = True):
    """Set up all required models."""
    logger.info("Starting model setup", models_dir=models_dir)
    
    downloader = ModelDownloader(models_dir)
    
    try:
        # Show model information
        info = downloader.get_model_info()
        logger.info("Model information", total_size_gb=info["total_size_gb"])
        
        # Download all models
        downloader.download_all_models(
            include_llm=include_llm,
            include_lora=include_lora
        )
        
        logger.info("Model setup completed successfully")
        
    except Exception as e:
        logger.error("Model setup failed", error=str(e))
        raise


def main():
    parser = argparse.ArgumentParser(description="Set up AI models for the platform")
    parser.add_argument("--models-dir", default="/opt/ai-worker/models", help="Models directory")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM models")
    parser.add_argument("--no-lora", action="store_true", help="Skip LoRA trainer")
    parser.add_argument("--info", action="store_true", help="Show model information only")
    
    args = parser.parse_args()
    
    if args.info:
        downloader = ModelDownloader(args.models_dir)
        info = downloader.get_model_info()
        
        print(f"Available models: {info['total_size_gb']:.1f} GB total")
        print(f"Models directory: {info['models_dir']}")
        
        for category, models in info["models"].items():
            print(f"\n{category.upper()}:")
            for name, config in models.items():
                print(f"  {name}: {config['size_gb']} GB")
        return
    
    # Run async setup
    asyncio.run(setup_models(
        models_dir=args.models_dir,
        include_llm=not args.no_llm,
        include_lora=not args.no_lora
    ))


if __name__ == "__main__":
    main()


