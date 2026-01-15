"""
⚠️ DEPRECATED: Old Export System

This module is deprecated. Please use the new template-based exporter:
- src.core.templates.exporter - New template exporter
- src.core.pipeline - New unified pipeline

See DEPRECATED.md for migration guide.
"""
import warnings

warnings.warn(
    "src.core.export is deprecated. "
    "Use src.core.templates.exporter instead. "
    "See src/core/export/DEPRECATED.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)
