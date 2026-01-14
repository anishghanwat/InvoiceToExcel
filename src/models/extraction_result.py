"""
Models for extraction results.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class TextBlock:
    """Represents a text block extracted from document."""
    id: str
    text: str
    confidence: float
    geometry: Dict[str, Any]
    block_type: str


@dataclass
class KeyValuePair:
    """Represents a key-value pair extracted from document."""
    key: str
    value: str
    key_confidence: float
    key_id: str


@dataclass
class ExtractionSummary:
    """Summary of extraction results."""
    total_blocks: int
    pages: int
    lines: int
    words: int
    key_value_pairs: int
    tables: int
    cells: int


@dataclass
class ExtractionResult:
    """Complete extraction result from document processing."""
    
    input_file: str
    summary: ExtractionSummary
    text_blocks: List[TextBlock] = field(default_factory=list)
    key_value_pairs: List[KeyValuePair] = field(default_factory=list)
    raw_textract_response: Optional[Dict[str, Any]] = None
    formatted_response: Optional[Dict[str, Any]] = None
    
    def get_all_text(self) -> str:
        """Get all extracted text as a single string."""
        return '\n'.join(block.text for block in self.text_blocks)
    
    def get_high_confidence_blocks(self, threshold: float = 90.0) -> List[TextBlock]:
        """Get text blocks with confidence above threshold."""
        return [block for block in self.text_blocks if block.confidence >= threshold]
    
    def get_low_confidence_blocks(self, threshold: float = 70.0) -> List[TextBlock]:
        """Get text blocks with confidence below threshold."""
        return [block for block in self.text_blocks if block.confidence < threshold]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'input_file': self.input_file,
            'summary': {
                'total_blocks': self.summary.total_blocks,
                'pages': self.summary.pages,
                'lines': self.summary.lines,
                'words': self.summary.words,
                'key_value_pairs': self.summary.key_value_pairs,
                'tables': self.summary.tables,
                'cells': self.summary.cells
            },
            'text_blocks': [
                {
                    'id': block.id,
                    'text': block.text,
                    'confidence': block.confidence,
                    'geometry': block.geometry,
                    'block_type': block.block_type
                }
                for block in self.text_blocks
            ],
            'key_value_pairs': [
                {
                    'key': kv.key,
                    'value': kv.value,
                    'key_confidence': kv.key_confidence,
                    'key_id': kv.key_id
                }
                for kv in self.key_value_pairs
            ]
        }