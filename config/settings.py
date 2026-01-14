"""
Application settings and configuration.
"""
import os
from pathlib import Path


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Directory paths
SRC_DIR = PROJECT_ROOT / "src"
CONFIG_DIR = PROJECT_ROOT / "config"
DOCS_DIR = PROJECT_ROOT / "docs"
TESTS_DIR = PROJECT_ROOT / "tests"
OUTPUT_DIR = PROJECT_ROOT / "output"
SAMPLES_DIR = PROJECT_ROOT / "samples"
LOGS_DIR = PROJECT_ROOT / "logs"

# File settings
SUPPORTED_FORMATS = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# AWS settings
DEFAULT_AWS_REGION = 'us-east-1'
TEXTRACT_TIMEOUT_SECONDS = 60

# Processing settings
DEFAULT_CONFIDENCE_THRESHOLD = 70.0
MAX_CSV_ROWS = 1000
DEFAULT_OUTPUT_ENCODING = 'utf-8'

# CSV settings
CSV_DELIMITER = ','
CSV_QUOTE_CHAR = '"'
CSV_ESCAPE_CHAR = '\\'

# Logging settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LOG_LEVEL = 'INFO'

# Field mapping settings
FIELD_MAPPINGS_FILE = CONFIG_DIR / "field_mappings.json"

# Environment file
ENV_FILE = PROJECT_ROOT / ".env"

# Create directories if they don't exist
def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        OUTPUT_DIR,
        LOGS_DIR,
        SAMPLES_DIR
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)


# Application metadata
APP_NAME = "InvoiceToExcel"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Document text extraction and CSV conversion tool using AWS Textract"
APP_AUTHOR = "Invoice Processing Team"

# Feature flags
ENABLE_NORMALIZATION = False  # Will be enabled when normalization layer is implemented
ENABLE_WEB_INTERFACE = False  # Future feature
ENABLE_BATCH_PROCESSING = False  # Future feature
ENABLE_TEMPLATE_LEARNING = False  # Future feature