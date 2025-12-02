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
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Console formatter
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
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
        logger.addHandler(file_handler)
    
    # Don't propagate to root logger (to avoid duplicate logs)
    # But child loggers SHOULD propagate to this logger
    logger.propagate = False
    
    # Set logging level for the entire 'rick_bot' hierarchy
    # This ensures all child loggers (e.g., 'rick_bot.llm.client') inherit the level
    logging.getLogger("rick_bot").setLevel(level)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name (will be prefixed with 'rick_bot' if not already)
        
    Returns:
        Logger instance that inherits from rick_bot parent logger
    """
    # If name is provided, make it a child of rick_bot
    if name and name != "rick_bot":
        # Extract just the module name (e.g., "src.bot.llm_integration" -> "bot.llm_integration")
        module_parts = name.split(".")
        if module_parts[0] == "src":
            module_parts = module_parts[1:]  # Remove 'src' prefix
        
        # Create child logger name under rick_bot hierarchy
        child_name = ".".join(module_parts)
        logger_name = f"rick_bot.{child_name}"
    else:
        logger_name = "rick_bot"
    
    logger = logging.getLogger(logger_name)
    
    # Child loggers should propagate to parent
    if logger_name != "rick_bot":
        logger.propagate = True
        # Don't set handlers on child loggers - they'll use parent's handlers
        if not logger.handlers:
            logger.handlers = []
    
    return logger

