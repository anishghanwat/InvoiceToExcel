"""
⚠️ DEPRECATED: Old Normalization Pipeline

This module is deprecated. Please use the new architecture:
- src.core.normalize - New canonical builder
- src.core.pipeline - New unified pipeline
- src.core.templates - New template engine

See DEPRECATED.md for migration guide.
"""
import warnings

warnings.warn(
    "src.core.normalization is deprecated. "
    "Use src.core.normalize and src.core.pipeline instead. "
    "See src/core/normalization/DEPRECATED.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)
