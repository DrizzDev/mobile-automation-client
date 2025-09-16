"""Logging utilities for mobile automation service."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from config import config


def setup_logging(
    name: str = "mobile-automation", 
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """Set up logging with both console and file handlers."""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level or config.log_level))
    
    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(config.log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log file is specified)
    log_file_path = log_file or config.log_file_path
    if log_file_path:
        # Ensure log directory exists
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(getattr(logging, config.log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def trace(message: str, logger: Optional[logging.Logger] = None) -> None:
    """Log a trace message."""
    if logger is None:
        logger = get_logger()
    logger.debug(f"TRACE: {message}")


def error(message: str, exception: Optional[Exception] = None, logger: Optional[logging.Logger] = None) -> None:
    """Log an error message with optional exception details."""
    if logger is None:
        logger = get_logger()
    
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=True)
    else:
        logger.error(message)


def get_logger(name: str = "mobile-automation") -> logging.Logger:
    """Get or create a logger instance."""
    return setup_logging(name)


# Default logger instance
default_logger = get_logger()
