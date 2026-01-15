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
DEFAULT_AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
TEXTRACT_TIMEOUT_SECONDS = int(os.getenv('TEXTRACT_TIMEOUT_SECONDS', '60'))
TEXTRACT_MAX_RETRIES = int(os.getenv('TEXTRACT_MAX_RETRIES', '3'))
TEXTRACT_RETRY_INITIAL_DELAY = float(os.getenv('TEXTRACT_RETRY_INITIAL_DELAY', '1.0'))
TEXTRACT_RETRY_MAX_DELAY = float(os.getenv('TEXTRACT_RETRY_MAX_DELAY', '60.0'))

# Processing settings
DEFAULT_CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '70.0'))
MAX_CSV_ROWS = int(os.getenv('MAX_CSV_ROWS', '1000'))
DEFAULT_OUTPUT_ENCODING = os.getenv('OUTPUT_ENCODING', 'utf-8')
PIPELINE_TIMEOUT_SECONDS = float(os.getenv('PIPELINE_TIMEOUT_SECONDS', '300.0'))  # 5 minutes
AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', '2'))
AI_TIMEOUT_SECONDS = float(os.getenv('AI_TIMEOUT_SECONDS', '30.0'))

# CSV settings
CSV_DELIMITER = ','
CSV_QUOTE_CHAR = '"'
CSV_ESCAPE_CHAR = '\\'

# Logging settings
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
DEFAULT_LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
ENABLE_STRUCTURED_LOGGING = os.getenv('ENABLE_STRUCTURED_LOGGING', 'true').lower() == 'true'

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
ENABLE_NORMALIZATION = os.getenv('ENABLE_NORMALIZATION', 'true').lower() == 'true'
ENABLE_WEB_INTERFACE = os.getenv('ENABLE_WEB_INTERFACE', 'false').lower() == 'true'
ENABLE_BATCH_PROCESSING = os.getenv('ENABLE_BATCH_PROCESSING', 'false').lower() == 'true'
ENABLE_TEMPLATE_LEARNING = os.getenv('ENABLE_TEMPLATE_LEARNING', 'false').lower() == 'true'
ENABLE_AI_FIXING = os.getenv('ENABLE_AI_FIXING', 'true').lower() == 'true'
ENABLE_GRACEFUL_DEGRADATION = os.getenv('ENABLE_GRACEFUL_DEGRADATION', 'true').lower() == 'true'

# Bulk Processing Settings
BULK_MAX_WORKERS = int(os.getenv('BULK_MAX_WORKERS', '3'))
BULK_CONSOLIDATED_OUTPUT = os.getenv('BULK_CONSOLIDATED_OUTPUT', 'true').lower() == 'true'
BULK_SKIP_EXISTING = os.getenv('BULK_SKIP_EXISTING', 'false').lower() == 'true'
BULK_PROGRESS_INTERVAL = float(os.getenv('BULK_PROGRESS_INTERVAL', '1.0'))  # seconds