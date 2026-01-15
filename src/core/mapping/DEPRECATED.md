# ⚠️ DEPRECATED - Old CSV Mapping System

This directory contains the **old CSV mapping system** which has been replaced by the new template-based architecture.

## Migration Guide

**New Architecture Location:**
- `src/core/templates/` - New template engine (JSON-based configuration)
- `src/core/pipeline.py` - New unified pipeline

## What Changed

The old mapping system had:
- `CSVMapper` - Column-based mapping
- `AIMapper` - AI-powered mapping
- `ProfessionalCSVMapper` - Specialized mapping

The new architecture:
- **Template-based** - JSON/YAML configuration files
- **Flexible** - User-defined templates, not code
- **Finance-grade** - Works with canonical model (extraction-only)
- **Extensible** - Easy to add new output formats

## Migration Steps

1. **Create templates instead of mapping code:**
   ```json
   {
     "name": "My Template",
     "columns": [
       {
         "header": "Invoice Number",
         "path": "invoice.invoice_number"
       },
       {
         "header": "Total",
         "path": "totals.total",
         "transform": "number:2"
       }
     ]
   }
   ```

2. **Use template parser:**
   ```python
   from src.core.templates.template_parser import TemplateParser
   
   parser = TemplateParser()
   template = parser.parse_from_file('templates/my_template.json')
   ```

3. **Export with template:**
   ```python
   from src.core.pipeline import InvoiceProcessingPipeline
   
   pipeline = InvoiceProcessingPipeline()
   result = pipeline.process_invoice(
       file_path='invoice.pdf',
       template=template,
       output_format='csv'
   )
   ```

## Removal Date

This directory will be removed in a future release. Please migrate to the new template-based architecture.
