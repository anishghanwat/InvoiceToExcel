"""
Canonical Builder - Creates canonical invoice structure.
Extraction is now done by Semantic Extractor (AI-driven).
"""
from typing import Dict, Any, Optional
from datetime import datetime
from .canonical_schema import CanonicalSchema


class CanonicalBuilder:
    """
    Creates canonical invoice model structure.
    
    Note: Field extraction is now handled by SemanticExtractor (AI-driven).
    This class just creates the empty structure.
    """
    
    def __init__(self):
        """Initialize canonical builder."""
        self.schema = CanonicalSchema()
    
    def create_empty(self) -> Dict[str, Any]:
        """
        Create empty canonical invoice structure.
        
        Returns:
            Empty canonical invoice model with all fields set to None
        """
        canonical = self.schema.create_empty()
        
        # Set metadata
        canonical["metadata"]["extraction_date"] = datetime.now().isoformat()
        canonical["metadata"]["source"] = "textract"
        
        return canonical
    
    def build(self, textract_results: Dict[str, Any], document_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Create canonical structure (extraction now done by SemanticExtractor).
        
        This method is kept for backward compatibility but just creates empty structure.
        The actual extraction is done by SemanticExtractor in the pipeline.
        
        Args:
            textract_results: Raw Textract extraction results (not used here, kept for compatibility)
            document_text: Optional full document text (not used here, kept for compatibility)
            
        Returns:
            Empty canonical invoice model
        """
        return self.create_empty()
