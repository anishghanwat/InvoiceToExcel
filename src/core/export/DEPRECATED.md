# ⚠️ DEPRECATED - Old Export System

This directory contains the **old export system** which has been replaced by the new template-based exporter.

## Migration Guide

**New Architecture Location:**
- `src/core/templates/exporter.py` - New template-based exporter
- `src/core/pipeline.py` - New unified pipeline

## What Changed

The old export system had:
- `CSVExporter` - Direct CSV export
- `ExcelExporter` - Excel export (if exists)

The new architecture:
- **TemplateExporter** - Works with templates
- **Flexible** - Same exporter for CSV, Excel, JSON
- **Template-driven** - Output format defined by template configuration

## Migration Steps

1. **Use template exporter:**
   ```python
   from src.core.templates.exporter import TemplateExporter
   from src.core.templates.template_parser import TemplateParser
   
   parser = TemplateParser()
   template = parser.parse_from_file('templates/my_template.json')
   
   exporter = TemplateExporter()
   exporter.export_to_csv(canonical, template, 'output.csv')
   ```

2. **Or use pipeline (recommended):**
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

This directory will be removed in a future release. Please migrate to the new template-based exporter.
