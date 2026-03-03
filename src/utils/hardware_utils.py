# -*- coding: utf-8 -*-
"""
hardware_utils.py — GPU and system hardware detection utilities
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


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


def is_safe_to_operate(temp_limit: float = 82.0, vram_min_mb: int = 256) -> bool:
    """
    Check if system is safe to start a heavy job.
    
    Criteria:
    1. GPU Temperature < temp_limit (default 82C)
    2. VRAM Free > vram_min_mb (default 256MB)
    
    Returns:
        True if safe, False if throttling needed.
    """
    # 1. Check VRAM
    gpu_info = get_gpu_info()
    if gpu_info['available']:
        if gpu_info['vram_free_mb'] < vram_min_mb:
            logger.warning(f"[Hardware] Low VRAM: {gpu_info['vram_free_mb']}MB < {vram_min_mb}MB")
            return False
            
    # 2. Check Temperature
    temp = get_gpu_temperature()
    if temp > temp_limit:
        logger.warning(f"[Hardware] GPU Overheating: {temp}C > {temp_limit}C")
        return False
        
    return True


def check_resource_availability(model_type: str = "generic") -> bool:
    """
    Check if system has enough resources for a specific model type.
    
    Args:
        model_type: 'vision' (heavy), 'analysis' (medium), 'chat' (light)
        
    Returns:
        True if resources are sufficient.
    """
    # Define constraints (MB)
    constraints = {
        "vision": 4096,    # Qwen2-VL needs ~4GB
        "analysis": 2048,  # Llama-3-8B needs ~2GB (quantized)
        "chat": 1024,      # TinyLlama / DeepSeek-R1-Distill needs ~1GB
        "generic": 512
    }
    
    required = constraints.get(model_type, 512)
    return is_safe_to_operate(temp_limit=85.0, vram_min_mb=required)
