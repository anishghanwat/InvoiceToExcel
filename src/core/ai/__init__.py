"""
AI Module - AI-driven components for invoice processing.
"""
from .ai_client import AIClient
from .semantic_extractor import SemanticExtractor
from .schema_inferencer import SchemaInferencer
from .dynamic_mapper import DynamicMapper
from .semantic_validator import SemanticValidator
from .learning_engine import LearningEngine

# Keep old canonical_fixer for backward compatibility (deprecated)
from .canonical_fixer import CanonicalFixer

__all__ = [
    'AIClient',
    'SemanticExtractor',
    'SchemaInferencer',
    'DynamicMapper',
    'SemanticValidator',
    'LearningEngine',
    'CanonicalFixer',  # Deprecated
]
