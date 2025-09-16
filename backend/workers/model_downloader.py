#!/usr/bin/env python3
"""
Model Downloader for AI Generation Platform
Downloads and caches AI models for GPU workers
"""

import os
import sys
import argparse
import requests
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
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


class ModelDownloader:
    """Downloads and manages AI models for the platform."""
    
    def __init__(self, models_dir: str = "/opt/ai-worker/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model configurations
        self.diffusion_models = {
            "sdxl-base": {
                "repo_id": "stabilityai/stable-diffusion-xl-base-1.0",
                "type": "diffusion",
                "size_gb": 6.9
            },
            "sdxl-refiner": {
                "repo_id": "stabilityai/stable-diffusion-xl-refiner-1.0", 
                "type": "diffusion",
                "size_gb": 6.9
            },
            "sdxl-turbo": {
                "repo_id": "stabilityai/sdxl-turbo",
                "type": "diffusion", 
                "size_gb": 4.6
            }
        }
        
        self.llm_models = {
            "llama-3.1-8b": {
                "repo_id": "meta-llama/Llama-3.1-8B-Instruct",
                "type": "llm",
                "size_gb": 16.0
            },
            "llama-3.1-70b": {
                "repo_id": "meta-llama/Llama-3.1-70B-Instruct",
                "type": "llm", 
                "size_gb": 140.0
            },
            "mistral-7b": {
                "repo_id": "mistralai/Mistral-7B-Instruct-v0.3",
                "type": "llm",
                "size_gb": 14.0
            },
            "qwen-2.5-72b": {
                "repo_id": "Qwen/Qwen2.5-72B-Instruct",
                "type": "llm",
                "size_gb": 144.0
            }
        }
        
        self.lora_models = {
            "sdxl-lora-trainer": {
                "repo_id": "kohya-ss/sd-scripts",
                "type": "lora_trainer",
                "size_gb": 2.0
            }
        }
    
    def download_diffusion_model(self, model_name: str) -> str:
        """Download a diffusion model."""
        if model_name not in self.diffusion_models:
            raise ValueError(f"Unknown diffusion model: {model_name}")
        
        model_config = self.diffusion_models[model_name]
        model_path = self.models_dir / "diffusion" / model_name
        
        logger.info(f"Downloading diffusion model: {model_name}")
        
        try:
            # Download the model
            snapshot_download(
                repo_id=model_config["repo_id"],
                local_dir=str(model_path),
                local_dir_use_symlinks=False
            )
            
            logger.info(f"Successfully downloaded {model_name}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")
            raise
    
    def download_llm_model(self, model_name: str) -> str:
        """Download an LLM model."""
        if model_name not in self.llm_models:
            raise ValueError(f"Unknown LLM model: {model_name}")
        
        model_config = self.llm_models[model_name]
        model_path = self.models_dir / "llm" / model_name
        
        logger.info(f"Downloading LLM model: {model_name}")
        
        try:
            # Download the model
            snapshot_download(
                repo_id=model_config["repo_id"],
                local_dir=str(model_path),
                local_dir_use_symlinks=False
            )
            
            logger.info(f"Successfully downloaded {model_name}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")
            raise
    
    def download_lora_trainer(self) -> str:
        """Download LoRA training dependencies."""
        model_name = "sdxl-lora-trainer"
        model_config = self.lora_models[model_name]
        model_path = self.models_dir / "lora" / model_name
        
        logger.info("Downloading LoRA trainer")
        
        try:
            # Clone the repository
            import subprocess
            subprocess.run([
                "git", "clone", 
                f"https://huggingface.co/{model_config['repo_id']}",
                str(model_path)
            ], check=True)
            
            logger.info("Successfully downloaded LoRA trainer")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Failed to download LoRA trainer: {e}")
            raise
    
    def download_all_models(self, include_llm: bool = True, include_lora: bool = True):
        """Download all required models."""
        logger.info("Starting model download process")
        
        # Download diffusion models
        for model_name in self.diffusion_models:
            try:
                self.download_diffusion_model(model_name)
            except Exception as e:
                logger.error(f"Failed to download {model_name}: {e}")
        
        # Download LLM models if requested
        if include_llm:
            for model_name in self.llm_models:
                try:
                    self.download_llm_model(model_name)
                except Exception as e:
                    logger.error(f"Failed to download {model_name}: {e}")
        
        # Download LoRA trainer if requested
        if include_lora:
            try:
                self.download_lora_trainer()
            except Exception as e:
                logger.error(f"Failed to download LoRA trainer: {e}")
        
        logger.info("Model download process completed")
    
    def get_model_info(self) -> dict:
        """Get information about available models."""
        total_size = 0
        models = {}
        
        for category, model_dict in [
            ("diffusion", self.diffusion_models),
            ("llm", self.llm_models),
            ("lora", self.lora_models)
        ]:
            models[category] = {}
            for name, config in model_dict.items():
                models[category][name] = {
                    "size_gb": config["size_gb"],
                    "repo_id": config["repo_id"]
                }
                total_size += config["size_gb"]
        
        return {
            "models": models,
            "total_size_gb": total_size,
            "models_dir": str(self.models_dir)
        }


def main():
    parser = argparse.ArgumentParser(description="Download AI models for GPU workers")
    parser.add_argument("--model", help="Specific model to download")
    parser.add_argument("--all", action="store_true", help="Download all models")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM models")
    parser.add_argument("--no-lora", action="store_true", help="Skip LoRA trainer")
    parser.add_argument("--info", action="store_true", help="Show model information")
    parser.add_argument("--models-dir", default="/opt/ai-worker/models", help="Models directory")
    
    args = parser.parse_args()
    
    downloader = ModelDownloader(args.models_dir)
    
    if args.info:
        info = downloader.get_model_info()
        print(f"Available models: {info['total_size_gb']:.1f} GB total")
        for category, models in info["models"].items():
            print(f"\n{category.upper()}:")
            for name, config in models.items():
                print(f"  {name}: {config['size_gb']} GB")
        return
    
    if args.model:
        # Download specific model
        if args.model in downloader.diffusion_models:
            downloader.download_diffusion_model(args.model)
        elif args.model in downloader.llm_models:
            downloader.download_llm_model(args.model)
        else:
            print(f"Unknown model: {args.model}")
            sys.exit(1)
    
    elif args.all:
        # Download all models
        downloader.download_all_models(
            include_llm=not args.no_llm,
            include_lora=not args.no_lora
        )
    
    else:
        print("Use --help for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()


