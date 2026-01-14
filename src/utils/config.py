"""
Configuration management utilities.
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for the application."""
    
    def __init__(self, env_file: str = ".env"):
        """Initialize configuration."""
        self.env_file = env_file
        self._load_environment()
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
    
    def get_aws_config(self) -> Dict[str, str]:
        """Get AWS configuration from environment."""
        return {
            'access_key_id': os.getenv('AWS_ACCESS_KEY_ID', ''),
            'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            'region': os.getenv('AWS_REGION', 'us-east-1'),
            's3_bucket': os.getenv('S3_BUCKET_NAME', '')
        }
    
    def validate_aws_config(self) -> bool:
        """Validate that required AWS configuration is present."""
        config = self.get_aws_config()
        return bool(config['access_key_id'] and config['secret_access_key'])
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return {
            'max_file_size_mb': int(os.getenv('MAX_FILE_SIZE_MB', '10')),
            'output_directory': os.getenv('OUTPUT_DIRECTORY', 'output'),
            'temp_directory': os.getenv('TEMP_DIRECTORY', 'temp'),
            'confidence_threshold': float(os.getenv('CONFIDENCE_THRESHOLD', '70.0'))
        }
    
    def get_csv_config(self) -> Dict[str, Any]:
        """Get CSV export configuration."""
        return {
            'default_encoding': os.getenv('CSV_ENCODING', 'utf-8'),
            'delimiter': os.getenv('CSV_DELIMITER', ','),
            'include_confidence': os.getenv('CSV_INCLUDE_CONFIDENCE', 'false').lower() == 'true',
            'max_rows': int(os.getenv('CSV_MAX_ROWS', '1000'))
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return os.getenv(key, default)
    
    def set(self, key: str, value: str) -> None:
        """Set environment variable."""
        os.environ[key] = value
    
    def __str__(self) -> str:
        """String representation of configuration."""
        aws_config = self.get_aws_config()
        processing_config = self.get_processing_config()
        
        return f"""Configuration:
  AWS Region: {aws_config['region']}
  AWS Credentials: {'✓' if self.validate_aws_config() else '✗'}
  Max File Size: {processing_config['max_file_size_mb']}MB
  Output Directory: {processing_config['output_directory']}
  Confidence Threshold: {processing_config['confidence_threshold']}%
"""