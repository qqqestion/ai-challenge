"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from pythonjsonlogger import jsonlogger


def setup_logger(
    name: str = "rick_bot",
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """Setup application logger with console and file handlers.
    
    Args:
        name: Logger name (used for file naming)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logger for 'src' package so all child loggers inherit handlers
    src_logger = logging.getLogger("src")
    src_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    src_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Console formatter
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    src_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=log_path / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        
        # JSON formatter for file logs
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(json_formatter)
        src_logger.addHandler(file_handler)
    
    # Prevent propagation to root logger to avoid third-party library logs
    src_logger.propagate = False
    
    # Get the specific logger (will inherit handlers from src logger via propagation)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Allow propagation to src logger so all child loggers use src handlers
    logger.propagate = True
    
    # Set logging level for the entire 'rick_bot' hierarchy
    # This ensures all child loggers (e.g., 'rick_bot.llm.client') inherit the level
    logging.getLogger("rick_bot").setLevel(level)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name (defaults to 'rick_bot')
        If name starts with 'src.', it will inherit handlers from 'src' logger
        
    Returns:
        Logger instance
    """
    logger_name = name or "rick_bot"
    logger = logging.getLogger(logger_name)
    
    # Ensure child loggers propagate to parent 'src' logger
    # This allows all src.* loggers to use handlers from 'src' logger
    if logger_name.startswith("src.") or logger_name == "src":
        # Child loggers should propagate to parent
        logger.propagate = True
        # Set level to match parent if not already set
        if logger.level == logging.NOTSET:
            parent_logger = logging.getLogger("src")
            if parent_logger.level != logging.NOTSET:
                logger.setLevel(parent_logger.level)
    
    return logger

