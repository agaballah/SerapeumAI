# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0

"""
path_validator.py — Security validation for file paths
------------------------------------------------------
Prevents path traversal attacks and validates file access.
"""

import os
from typing import Optional


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def validate_attachment_path(
    path: str,
    project_root: Optional[str] = None,
    allow_external: bool = True
) -> str:
    """
    Validate and sanitize a file path for attachment.
    
    Args:
        path: The file path to validate
        project_root: Optional project root directory
        allow_external: If False, only allow files within project_root
        
    Returns:
        Absolute, normalized path
        
    Raises:
        PathValidationError: If path is invalid or unsafe
    """
    # Normalize path
    try:
        real_path = os.path.realpath(path)
    except Exception as e:
        raise PathValidationError(f"Invalid path: {e}")
    
    # Check file exists
    if not os.path.exists(real_path):
        raise PathValidationError(f"File does not exist: {path}")
    
    # Check is a file, not a directory
    if not os.path.isfile(real_path):
        raise PathValidationError(f"Path is not a file: {path}")
    
    # Check file is readable
    if not os.access(real_path, os.R_OK):
        raise PathValidationError(f"File is not readable: {path}")
    
    # Check for forbidden system directories
    forbidden_dirs = get_forbidden_directories()
    for forbidden in forbidden_dirs:
        if real_path.startswith(forbidden):
            raise PathValidationError(f"Access to system directory forbidden: {path}")
    
    # If project_root specified and allow_external=False, ensure within project
    if project_root and not allow_external:
        real_root = os.path.realpath(project_root)
        if not real_path.startswith(real_root):
            raise PathValidationError(f"File must be within project directory: {path}")
    
    # Check file size (prevent loading huge files into memory)
    max_size = 500 * 1024 * 1024  # 500MB
    file_size = os.path.getsize(real_path)
    if file_size > max_size:
        raise PathValidationError(f"File too large: {file_size / 1024 / 1024:.1f}MB (max 500MB)")
    
    return real_path


def get_forbidden_directories() -> list:
    """Get list of forbidden system directories."""
    forbidden = []
    
    # Windows system directories
    if os.name == 'nt':
        system_drive = os.environ.get('SystemDrive', 'C:')
        forbidden.extend([
            os.path.join(system_drive, '\\Windows'),
            os.path.join(system_drive, '\\Program Files'),
            os.path.join(system_drive, '\\Program Files (x86)'),
            os.path.join(system_drive, '\\ProgramData'),
            os.path.join(system_drive, '\\System Volume Information'),
        ])
    
    # Unix/Linux system directories
    else:
        forbidden.extend([
            '/bin',
            '/sbin',
            '/usr/bin',
            '/usr/sbin',
            '/etc',
            '/sys',
            '/proc',
            '/dev',
            '/boot',
        ])
    
    return forbidden


def validate_project_directory(path: str) -> str:
    """
    Validate a project directory path.
    
    Args:
        path: Directory path to validate
        
    Returns:
        Absolute, normalized path
        
    Raises:
        PathValidationError: If directory is invalid
    """
    try:
        real_path = os.path.realpath(path)
    except Exception as e:
        raise PathValidationError(f"Invalid path: {e}")
    
    # Check is a directory
    if not os.path.isdir(real_path):
        raise PathValidationError(f"Path is not a directory: {path}")
    
    # Check is writable
    if not os.access(real_path, os.W_OK):
        raise PathValidationError(f"Directory is not writable: {path}")
    
    # Check for forbidden directories
    forbidden_dirs = get_forbidden_directories()
    for forbidden in forbidden_dirs:
        if real_path.startswith(forbidden):
            raise PathValidationError(f"Cannot use system directory as project: {path}")
    
    return real_path


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing unsafe characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove null bytes
    filename = filename.replace('\0', '')
    
    # Remove control characters
    filename = ''.join(c for c in filename if ord(c) >= 32)
    
    # Replace other unsafe characters
    unsafe_chars = '<>:"|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    max_len = 255
    if len(filename) > max_len:
        name, ext = os.path.splitext(filename)
        name = name[:max_len - len(ext)]
        filename = name + ext
    
    return filename
