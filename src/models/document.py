"""
Document model for representing input documents.
"""
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class Document:
    """Represents an input document for processing."""
    
    file_path: str
    file_name: str
    file_size: int
    file_type: str
    content: Optional[bytes] = None
    
    @classmethod
    def from_file_path(cls, file_path: str) -> 'Document':
        """Create Document from file path."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return cls(
            file_path=str(path.absolute()),
            file_name=path.name,
            file_size=path.stat().st_size,
            file_type=path.suffix.lower(),
            content=None
        )
    
    def load_content(self) -> bytes:
        """Load file content into memory."""
        if self.content is None:
            with open(self.file_path, 'rb') as f:
                self.content = f.read()
        return self.content
    
    def is_supported_format(self) -> bool:
        """Check if document format is supported."""
        supported_formats = {'.pdf', '.png', '.jpg', '.jpeg'}
        return self.file_type in supported_formats
    
    def __str__(self) -> str:
        return f"Document({self.file_name}, {self.file_size} bytes)"