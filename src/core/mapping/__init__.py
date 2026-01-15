"""
⚠️ DEPRECATED: Old CSV Mapping System

This module is deprecated. Please use the new template-based architecture:
- src.core.templates - New template engine
- src.core.pipeline - New unified pipeline

See DEPRECATED.md for migration guide.
"""
import warnings

warnings.warn(
    "src.core.mapping is deprecated. "
    "Use src.core.templates instead. "
    "See src/core/mapping/DEPRECATED.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)
