#!/usr/bin/env python3
import os
import sys
import logging
from typing import Optional, Dict, Any

def get_logs_dir() -> str:
    """
    Get the standardized logs directory path.
    
    Returns:
        str: Path to the logs directory
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def setup_logging(log_name: str, console: bool = True, file: bool = True, level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging with standardized format and paths.
    
    Args:
        log_name: Name of the log file (without .log extension)
        console: Whether to log to console
        file: Whether to log to file
        level: Logging level
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logs_dir = get_logs_dir()
    log_file = os.path.join(logs_dir, f"{log_name}.log")
    
    # Create a unique logger
    logger = logging.getLogger(log_name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Set up formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add handlers
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def setup_script_logging(script_name: Optional[str] = None) -> logging.Logger:
    """
    Setup logging for a script using the file's name.
    This is a convenience wrapper for setup_logging.
    
    Args:
        script_name: Optional script name override. If None, derives name from calling file.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    if script_name is None:
        # Get the caller module's filename
        import inspect
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if module:
            # Extract basename without extension
            script_name = os.path.splitext(os.path.basename(module.__file__))[0]
        else:
            script_name = "unknown"
    
    return setup_logging(script_name) 