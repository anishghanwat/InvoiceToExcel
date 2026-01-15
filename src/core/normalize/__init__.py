"""
Normalization module - Builds canonical invoice model from Textract output.
"""
from .canonical_schema import CanonicalSchema
from .canonical_builder import CanonicalBuilder

__all__ = ['CanonicalSchema', 'CanonicalBuilder']
