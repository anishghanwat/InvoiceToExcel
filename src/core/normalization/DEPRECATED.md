# ⚠️ DEPRECATED - Old Normalization Pipeline

This directory contains the **old 4-layer normalization pipeline** which has been replaced by the new finance-grade architecture.

## Migration Guide

**New Architecture Location:**
- `src/core/normalize/` - New canonical builder (extraction-only, no calculations)
- `src/core/pipeline.py` - New unified pipeline
- `src/core/templates/` - New template engine

## What Changed

The old normalization pipeline had:
- 4 layers (Deterministic → AI Semantic → Validation → AI Repair)
- Calculation logic
- Complex mapping

The new architecture:
- **Extraction-only** - No calculations, only extract what AWS Textract finds
- **Finance-grade** - Trust AWS confidence, point-to-point accuracy
- **Template-based** - Flexible output formats via configuration
- **Simpler** - Single canonical builder, optional AI fixing

## Migration Steps

1. **Update imports:**
   ```python
   # OLD
   from src.core.normalization.normalization_pipeline import NormalizationPipeline
   
   # NEW
   from src.core.pipeline import InvoiceProcessingPipeline
   ```

2. **Update usage:**
   ```python
   # OLD
   pipeline = NormalizationPipeline()
   result = pipeline.process(...)
   
   # NEW
   pipeline = InvoiceProcessingPipeline()
   result = pipeline.process_invoice(file_path, template=template)
   ```

3. **Use templates instead of mapping:**
   - Old: Custom mapping logic
   - New: JSON template configuration files

## Removal Date

This directory will be removed in a future release. Please migrate to the new architecture.
