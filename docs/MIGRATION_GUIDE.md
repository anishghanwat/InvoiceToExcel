# Migration Guide: Old Architecture → New Architecture

This guide helps you migrate from the old architecture to the new finance-grade, template-based architecture.

## Overview

The new architecture (Layer-2/Normalization) replaces:
- ❌ Old 4-layer normalization pipeline
- ❌ Old CSV mapping system
- ❌ Old export system

With:
- ✅ Finance-grade extraction-only canonical builder
- ✅ Template-based flexible export system
- ✅ Unified pipeline

## Key Changes

### 1. No More Calculations

**Old:** System calculated values (taxable_value = unit_price × quantity, etc.)

**New:** Only extracts what AWS Textract finds. No calculations, no assumptions.

### 2. Template-Based Export

**Old:** Code-based mapping (`CSVMapper`, `AIMapper`)

**New:** JSON template configuration files

### 3. Unified Pipeline

**Old:** Multiple separate components

**New:** Single `InvoiceProcessingPipeline` that handles everything

## Migration Steps

### For CLI Users

**Old:**
```bash
python -m src.cli invoice.pdf
```

**New:**
```bash
# Basic usage (same)
python -m src.interfaces.cli invoice.pdf

# With template
python -m src.interfaces.cli invoice.pdf --template templates/gstr1.json

# Export to JSON
python -m src.interfaces.cli invoice.pdf --format json

# Disable AI
python -m src.interfaces.cli invoice.pdf --no-ai
```

### For Interactive Users

**Old:**
```bash
python -m src.interactive_csv invoice.pdf
```

**New:**
```bash
python -m src.interfaces.interactive_csv invoice.pdf
```

The new interactive interface:
- Shows extraction summary
- Lets you choose from default templates
- Allows creating custom templates interactively

### For Programmatic Usage

**Old:**
```python
from src.core.extraction.document_processor import DocumentProcessor
from src.core.mapping.csv_mapper import CSVMapper

processor = DocumentProcessor()
results = processor.process_document('invoice.pdf')

mapper = CSVMapper()
columns = mapper.get_user_columns()
mappings = mapper.map_columns_to_data(columns, categorized_data)
csv_path = mapper.create_csv_output(columns, mappings, 'output.csv')
```

**New:**
```python
from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser

# Initialize pipeline
pipeline = InvoiceProcessingPipeline(use_ai=True)

# Load template (or use default)
parser = TemplateParser()
template = parser.parse_from_file('templates/gstr1.json')

# Process invoice
result = pipeline.process_invoice(
    file_path='invoice.pdf',
    template=template,
    output_format='csv',
    output_path='output/invoice.csv'
)

# Access results
canonical = result['canonical']
validation = result['validation']
output_file = result['output_file']
```

## Template Creation

### Old Way (Code)
```python
# Had to write code for mapping
mapper = CSVMapper()
columns = ['Invoice No', 'Date', 'Total']
# Complex mapping logic...
```

### New Way (Configuration)
```json
{
  "name": "My Template",
  "columns": [
    {
      "header": "Invoice No",
      "path": "invoice.invoice_number"
    },
    {
      "header": "Date",
      "path": "invoice.invoice_date",
      "transform": "date:DD-MM-YYYY"
    },
    {
      "header": "Total",
      "path": "totals.total",
      "transform": "number:2"
    }
  ]
}
```

## Available Templates

Default templates are in `templates/`:
- `simple_invoice.json` - One row per invoice (summary)
- `gstr1.json` - GSTR-1 export format (line items)
- `tally.json` - Tally import format
- `quickbooks.json` - QuickBooks import
- `xero.json` - Xero import
- `audit_trail.json` - Detailed audit trail

## Deprecated Modules

These modules are deprecated and will be removed:

- `src.core.normalization.*` → Use `src.core.normalize.*`
- `src.core.mapping.*` → Use `src.core.templates.*`
- `src.core.export.*` → Use `src.core.templates.exporter`

See `DEPRECATED.md` files in each directory for details.

## Benefits of New Architecture

1. **Finance-Grade Accuracy**: No calculations, only extraction
2. **Flexibility**: Easy to create new output formats via templates
3. **Maintainability**: Simpler codebase, clear separation of concerns
4. **Extensibility**: Add new templates without code changes
5. **User Control**: Users can define their own templates

## Questions?

- Check `docs/ARCHITECTURE.md` for architecture details
- See `templates/README.md` for template documentation
- Review `src/core/pipeline.py` for pipeline usage
