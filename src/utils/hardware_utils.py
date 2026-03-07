# -*- coding: utf-8 -*-
"""
hardware_utils.py â€” GPU and system hardware detection utilities
"""

import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Global lock to prevent concurrent VRAM-heavy operations (LLM load vs Embedding Init)
_VRAM_ORCHESTRATION_LOCK = threading.Lock()
_RESERVED_VRAM_MB: int = 0


def get_gpu_info() -> Dict[str, any]:
    """
    Detect GPU information including VRAM.

    Returns:
        {
            'available': bool,
            'vram_total_mb': int,
            'vram_used_mb': int,
            'vram_free_mb': int,
            'gpu_name': str,
            'gpu_driver': str,
            'method': str  # 'pynvml', 'torch', or 'none'
        }
    """
    # Try pynvml first (NVIDIA Management Library)
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode('utf-8')

        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        driver_version = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver_version, bytes):
            driver_version = driver_version.decode('utf-8')

        vram_total_mb = mem_info.total // (1024 * 1024)
        vram_used_mb = mem_info.used // (1024 * 1024)
        vram_free_mb = mem_info.free // (1024 * 1024)

        pynvml.nvmlShutdown()

        return {
            'available': True,
            'vram_total_mb': vram_total_mb,
            'vram_used_mb': vram_used_mb,
            'vram_free_mb': vram_free_mb,
            'gpu_name': gpu_name,
            'gpu_driver': driver_version,
            'method': 'pynvml'
        }
    except Exception as e:
        logger.debug(f"[Hardware] pynvml detection failed: {e}")

    # Try torch.cuda as fallback
    try:
        import torch
        if torch.cuda.is_available():
            device = torch.cuda.current_device()
            gpu_name = torch.cuda.get_device_name(device)

            # Get memory info in bytes
            vram_total = torch.cuda.get_device_properties(device).total_memory
            vram_allocated = torch.cuda.memory_allocated(device)
            vram_reserved = torch.cuda.memory_reserved(device)

            vram_total_mb = vram_total // (1024 * 1024)
            vram_used_mb = vram_allocated // (1024 * 1024)
            vram_free_mb = (vram_total - vram_reserved) // (1024 * 1024)

            return {
                'available': True,
                'vram_total_mb': vram_total_mb,
                'vram_used_mb': vram_used_mb,
                'vram_free_mb': vram_free_mb,
                'gpu_name': gpu_name,
                'gpu_driver': 'unknown',
                'method': 'torch'
            }
    except Exception as e:
        logger.debug(f"[Hardware] torch.cuda detection failed: {e}")

    # No GPU detected
    return {
        'available': False,
        'vram_total_mb': 0,
        'vram_used_mb': 0,
        'vram_free_mb': 0,
        'gpu_name': 'No GPU',
        'gpu_driver': 'N/A',
        'method': 'none'
    }


    return gpu_info['vram_free_mb'] >= required_mb


def get_gpu_temperature() -> float:
    """
    Get current GPU temperature in Celsius.
    Returns -1.0 if not available.
    """
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        # pynvml.nvmlShutdown() # Keep it open? Frequent init/shutdown might be overhead.
        # Check docs: nvmlInit is ref-counted in newer versions or safe to call multiple times?
        # Standard practice: Init once. But here we are utils. Let's shutdown to be safe / stateless.
        pynvml.nvmlShutdown()
        return float(temp)
    except Exception:
        return -1.0


def reserve_vram(mb: int) -> bool:
    """Reserve VRAM to prevent other processes/services from using it."""
    global _RESERVED_VRAM_MB
    info = get_gpu_info()
    if not info['available']:
        return True # CPU fallback is always 'reserved'

    with _VRAM_ORCHESTRATION_LOCK:
        if info['vram_free_mb'] - _RESERVED_VRAM_MB >= mb:
            _RESERVED_VRAM_MB += mb
            logger.info(f"[Hardware] Reserved {mb}MB VRAM. Total reserved: {_RESERVED_VRAM_MB}MB.")
            return True
        return False


def release_vram(mb: int):
    """Release previously reserved VRAM."""
    global _RESERVED_VRAM_MB
    with _VRAM_ORCHESTRATION_LOCK:
        _RESERVED_VRAM_MB = max(0, _RESERVED_VRAM_MB - mb)
        logger.info(f"[Hardware] Released {mb}MB VRAM. Remaining reserved: {_RESERVED_VRAM_MB}MB.")


def check_resource_availability(model_type: str = "generic") -> bool:
    """
    Check if system has enough resources for a specific model type.

    Args:
        model_type: 'vision' (heavy), 'analysis' (medium), 'chat' (light)

    Returns:
        True if resources are sufficient.
    """
    global _RESERVED_VRAM_MB

    # 1. Temperature Check (Critical Safety)
    temp = get_gpu_temperature()
    if temp > 85.0:
        logger.warning(f"[Hardware] GPU Overheating: {temp}C > 85.0C")
        return False

    # 2. VRAM Contentions Check
    # Define constraints (MB)
    constraints = {
        "vision": 4096,    # Qwen2-VL needs ~4GB
        "analysis": 2048,  # Llama-3-8B needs ~2GB (quantized)
        "chat": 1024,      # TinyLlama / DeepSeek-R1-Distill needs ~1GB
        "generic": 512
    }

    required = constraints.get(model_type, 512)
    info = get_gpu_info()

    if not info['available']:
        return True # CPU fallback is always 'available'

    return (info['vram_free_mb'] - _RESERVED_VRAM_MB) >= required
