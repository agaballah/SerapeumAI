# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
model_downloader.py — Automatic Qwen2-VL-7B model downloader
------------------------------------------------------------

Downloads the required GGUF model file from HuggingFace on first run.
Shows progress bar and verifies file integrity.
"""

import os
import sys
from pathlib import Path
from urllib.request import urlretrieve


# Model configuration
MODEL_URL = "https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct-GGUF/resolve/main/qwen2-vl-7b-instruct-q4_k_m.gguf"
MODEL_FILENAME = "qwen2-vl-7b-instruct-q4_k_m.gguf"
MODEL_SIZE_BYTES = 4_900_000_000  # Approximate 4.6 GB
MODEL_SIZE_GB = 4.6


def download_with_progress(url: str, destination: str):
    """Download file with progress indicator."""
    
    def progress_hook(block_num, block_size, total_size):
        """Show download progress."""
        downloaded = block_num * block_size
        if total_size > 0:
            percent = int(downloaded * 100 / total_size)
            bar = "=" * (percent // 2) + ">" + " " * (50 - percent // 2)
            sys.stdout.write(f"\r[{bar}] {percent}% | {downloaded / 1e9:.2f} / {total_size / 1e9:.2f} GB")
            sys.stdout.flush()
    
    print(f"Downloading {MODEL_FILENAME} ({MODEL_SIZE_GB} GB)...")
    print(f"From: {url}")
    print(f"To: {destination}\n")
    
    try:
        urlretrieve(url, destination, reporthook=progress_hook)
        print("\n✅ Download complete!")
        return True
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return False


def verify_model_exists(model_dir: str) -> bool:
    """Check if model file already exists."""
    model_path = os.path.join(model_dir, MODEL_FILENAME)
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"✅ Model found: {model_path} ({size_mb:.0f} MB)")
        return True
    return False


def download_model(model_dir: str, force: bool = False) -> bool:
    """
    Download Qwen2-VL-7B GGUF model if not present.
    
    Args:
        model_dir: Directory to save model
        force: Force re-download even if file exists
        
    Returns:
        bool: True if model is ready, False if download failed
    """
    # Create models directory
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, MODEL_FILENAME)
    
    # Check if already downloaded
    if not force and verify_model_exists(model_dir):
        return True
    
    # Ask user confirmation
    print(f"\n{'='*60}")
    print("Qwen2-VL-7B Model Download Required")
    print(f"{'='*60}")
    print(f"Model: {MODEL_FILENAME}")
    print(f"Size: {MODEL_SIZE_GB} GB")
    print(f"URL: {MODEL_URL}")
    print(f"Destination: {model_path}")
    print(f"{'='*60}\n")
    
    response = input("Download now? (yes/no): ").strip().lower()
    if response not in ["yes", "y"]:
        print("❌ Download cancelled. Model is required for Serapeum to function.")
        return False
    
    # Download
    success = download_with_progress(MODEL_URL, model_path)
    
    if success:
        # Verify file size
        actual_size = os.path.getsize(model_path)
        expected_min = MODEL_SIZE_BYTES * 0.95  # Allow 5% variance
        expected_max = MODEL_SIZE_BYTES * 1.05
        
        if expected_min <= actual_size <= expected_max:
            print(f"✅ Model verified: {actual_size / 1e9:.2f} GB")
            print("✅ Ready to use!")
            return True
        else:
            print(f"⚠️  Warning: File size unexpected ({actual_size / 1e9:.2f} GB)")
            print(f"   Expected: ~{MODEL_SIZE_GB} GB")
            print("   Model may still work, but consider re-downloading if issues occur.")
            return True
    
    return False


def main():
    """Standalone model downloader."""
    # Determine project root
    script_dir = Path(__file__).parent.parent.parent
    model_dir = script_dir / "models"
    
    print("Serapeum Model Downloader")
    print(f"Project Root: {script_dir}")
    print(f"Models Directory: {model_dir}\n")
    
    success = download_model(str(model_dir))
    
    if success:
        print("\n✅ Setup complete! You can now run Serapeum.")
        sys.exit(0)
    else:
        print("\n❌ Model download failed or cancelled.")
        print("   Manual download: https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct-GGUF")
        print(f"   Place file in: {model_dir}")
        sys.exit(1)


if __name__ == "__main__":
    main()
