"""
Logging utilities.
"""
import logging
import os
from datetime import datetime
from typing import Optional


class Logger:
    """Custom logger for the application."""
    
    def __init__(self, name: str = "InvoiceToExcel", log_file: Optional[str] = None):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
    
    def log_extraction_start(self, file_path: str) -> None:
        """Log extraction start."""
        self.info(f"Starting extraction for: {file_path}")
    
    def log_extraction_complete(self, file_path: str, duration: float) -> None:
        """Log extraction completion."""
        self.info(f"Extraction complete for {file_path} in {duration:.2f}s")
    
    def log_csv_creation(self, csv_path: str, rows: int, columns: int) -> None:
        """Log CSV creation."""
        self.info(f"CSV created: {csv_path} ({rows} rows, {columns} columns)")
    
    def log_error_with_context(self, error: Exception, context: str) -> None:
        """Log error with context."""
        self.error(f"Error in {context}: {str(error)}")


# Global logger instance
_global_logger: Optional[Logger] = None


def get_logger(name: str = "InvoiceToExcel", log_file: Optional[str] = None) -> Logger:
    """Get or create global logger instance."""
    global _global_logger
    
    if _global_logger is None:
        # Create log file path if not provided
        if log_file is None:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"invoice_processing_{timestamp}.log")
        
        _global_logger = Logger(name, log_file)
    
    return _global_logger