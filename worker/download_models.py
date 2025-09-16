#!/usr/bin/env python3
"""
Download AI models for the GPU worker.

Adds CLI flags and environment overrides for flexibility and idempotency.

Defaults are compatible with `worker/executor.py` which expects
`./models/sdxl-base` to exist.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

from huggingface_hub import snapshot_download


def human(path: Path) -> str:
    try:
        return str(path.resolve())
    except Exception:
        return str(path)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def already_exists(dir_path: Path) -> bool:
    # A lightweight check: directory exists and has files
    return dir_path.exists() and any(dir_path.iterdir())


def download_repo(
    repo_id: str,
    local_dir: Path,
    hf_token: Optional[str],
    cache_dir: Optional[Path],
    local_only: bool,
) -> None:
    ensure_dir(local_dir)
    snapshot_download(
        repo_id=repo_id,
        local_dir=human(local_dir),
        local_dir_use_symlinks=False,
        token=hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"),
        resume_download=True,
        local_files_only=local_only,
        cache_dir=human(cache_dir) if cache_dir else None,
    )


def download_models(
    models_dir: Path,
    include_refiner: bool,
    include_turbo: bool,
    hf_token: Optional[str],
    cache_dir: Optional[Path],
    local_only: bool,
) -> None:
    ensure_dir(models_dir)

    # SDXL Base (required for executor)
    sdxl_base_dir = models_dir / "sdxl-base"
    if already_exists(sdxl_base_dir):
        print(f"Skipping SDXL Base (already present): {human(sdxl_base_dir)}")
    else:
        print("Downloading Stable Diffusion XL Base 1.0…")
        download_repo(
            "stabilityai/stable-diffusion-xl-base-1.0",
            sdxl_base_dir,
            hf_token,
            cache_dir,
            local_only,
        )

    # SDXL Refiner (optional)
    if include_refiner:
        sdxl_refiner_dir = models_dir / "sdxl-refiner"
        if already_exists(sdxl_refiner_dir):
            print(f"Skipping SDXL Refiner (already present): {human(sdxl_refiner_dir)}")
        else:
            print("Downloading Stable Diffusion XL Refiner 1.0…")
            download_repo(
                "stabilityai/stable-diffusion-xl-refiner-1.0",
                sdxl_refiner_dir,
                hf_token,
                cache_dir,
                local_only,
            )

    # SDXL Turbo (optional, fast preview)
    if include_turbo:
        sdxl_turbo_dir = models_dir / "sdxl-turbo"
        if already_exists(sdxl_turbo_dir):
            print(f"Skipping SDXL Turbo (already present): {human(sdxl_turbo_dir)}")
        else:
            print("Downloading SDXL Turbo…")
            download_repo(
                "stabilityai/sdxl-turbo",
                sdxl_turbo_dir,
                hf_token,
                cache_dir,
                local_only,
            )

    print("Models are ready.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download AI models for the GPU worker")
    parser.add_argument(
        "--models-dir",
        default=os.environ.get("MODELS_DIR", "./models"),
        help="Directory to place models (env: MODELS_DIR)",
    )
    parser.add_argument(
        "--no-refiner",
        action="store_true",
        help="Skip downloading SDXL Refiner",
    )
    parser.add_argument(
        "--turbo",
        action="store_true",
        help="Also download SDXL Turbo",
    )
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"),
        help="Hugging Face token (env: HF_TOKEN)",
    )
    parser.add_argument(
        "--cache-dir",
        default=os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE") or os.environ.get("HUGGINGFACE_CACHE"),
        help="Hugging Face cache directory (env: HF_HOME/HUGGINGFACE_HUB_CACHE)",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Use only local cache; do not access network",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models_dir = Path(args.models_dir)

    print(f"Models directory: {human(models_dir)}")
    if args.hf_token:
        # Avoid logging token value
        print("Using Hugging Face token from CLI/env")
    if args.cache_dir:
        print(f"Using HF cache: {args.cache_dir}")
    if args.local_only:
        print("Local-only mode: will not download from network")

    try:
        download_models(
            models_dir=models_dir,
            include_refiner=not args.no_refiner,
            include_turbo=args.turbo,
            hf_token=args.hf_token,
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            local_only=bool(args.local_only),
        )
        return 0
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
    except Exception as e:
        print(f"Download failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
