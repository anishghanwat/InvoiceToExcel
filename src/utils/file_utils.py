"""
File utility functions.
"""
import os
from pathlib import Path
from typing import List, Optional


class FileUtils:
    """Utility functions for file operations."""
    
    SUPPORTED_FORMATS = {'.pdf', '.png', '.jpg', '.jpeg'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_file(file_path: str) -> bool:
        """
        Validate if file exists, has supported format, and is within size limits.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is valid
            
        Raises:
            Exception: If file is invalid
        """
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in FileUtils.SUPPORTED_FORMATS:
            raise Exception(f"Unsupported file format: {file_ext}. Supported: {', '.join(FileUtils.SUPPORTED_FORMATS)}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > FileUtils.MAX_FILE_SIZE:
            raise Exception(f"File too large: {file_size / (1024*1024):.1f}MB. Max size: {FileUtils.MAX_FILE_SIZE / (1024*1024)}MB")
        
        return True
    
    @staticmethod
    def ensure_directory(directory: str) -> str:
        """
        Ensure directory exists, create if it doesn't.
        
        Args:
            directory: Directory path
            
        Returns:
            Absolute path to directory
        """
        os.makedirs(directory, exist_ok=True)
        return os.path.abspath(directory)
    
    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """
        Get a safe filename by removing/replacing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe_filename = filename
        for char in invalid_chars:
            safe_filename = safe_filename.replace(char, '_')
        
        return safe_filename
    
    @staticmethod
    def get_unique_filename(base_path: str, extension: str = "") -> str:
        """
        Get a unique filename by adding numbers if file exists.
        
        Args:
            base_path: Base file path without extension
            extension: File extension (with dot)
            
        Returns:
            Unique file path
        """
        counter = 1
        original_path = f"{base_path}{extension}"
        
        if not os.path.exists(original_path):
            return original_path
        
        while True:
            new_path = f"{base_path}_{counter}{extension}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1
    
    @staticmethod
    def find_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
        """
        Find all files with specified extensions in directory.
        
        Args:
            directory: Directory to search
            extensions: List of extensions (with dots)
            
        Returns:
            List of file paths
        """
        files = []
        if not os.path.exists(directory):
            return files
        
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                file_ext = Path(file).suffix.lower()
                if file_ext in extensions:
                    files.append(file_path)
        
        return files