# Invoice Export Templates

This directory contains pre-configured templates for exporting invoices to various formats.

## Available Templates

### 1. **gstr1.json** - GSTR-1 Export Format
GST Return format for India. Line item level export with HSN and complete tax breakdown.

**Use case**: Filing GST returns in India
**Format**: One row per line item
**Includes**: HSN codes, CGST/SGST/IGST rates and amounts, place of supply

### 2. **tally.json** - Tally Import Format
Format for importing invoices into Tally accounting software.

**Use case**: Importing invoices into Tally
**Format**: One row per line item
**Includes**: Voucher details, party information, item details with taxes

### 3. **quickbooks.json** - QuickBooks Import Format
Format for importing invoices into QuickBooks accounting software.

**Use case**: Importing invoices into QuickBooks
**Format**: One row per line item
**Includes**: Customer details, item/service information, tax amounts

### 4. **xero.json** - Xero Import Format
Format for importing invoices into Xero accounting software.

**Use case**: Importing invoices into Xero
**Format**: One row per line item
**Includes**: Contact name, invoice details, inventory items, tax information

### 5. **simple_invoice.json** - Simple Invoice Summary
One row per invoice - summary format without line item details.

**Use case**: Quick invoice summaries, reporting
**Format**: One row per invoice
**Includes**: Invoice header, vendor/customer info, totals

### 6. **audit_trail.json** - Detailed Audit Trail
Comprehensive line item export with full audit information.

**Use case**: Detailed record keeping, audit requirements
**Format**: One row per line item
**Includes**: Complete invoice and line item details with all tax breakdowns

## Usage

### Python Code Example

```python
from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser
from src.core.templates.exporter import TemplateExporter

# Initialize
pipeline = InvoiceProcessingPipeline(use_ai=True)
template_parser = TemplateParser()
exporter = TemplateExporter()

# Process invoice
result = pipeline.process_invoice("invoice.pdf", output_format="json")
canonical = result["canonical"]

# Load a template
gstr1_template = template_parser.load_default_template("gstr1")

# Export using template
exporter.export_to_csv(canonical, gstr1_template, "output/gstr1_export.csv")
```

### Command Line (Future)

```bash
# Export to GSTR-1 format
python main.py export invoice.pdf --template gstr1

# Export to Tally format
python main.py export invoice.pdf --template tally

# List available templates
python main.py templates list
```

## Template Structure

Each template is a JSON file with this structure:

```json
{
  "name": "Template Name",
  "description": "What this template is for",
  "repeat": "line_items",  // or null for invoice-level
  "columns": [
    {
      "header": "Column Name",
      "path": "canonical.field.path",
      "transform": "date:DD-MM-YYYY"  // optional
    }
  ]
}
```

### Column Configuration

- **header**: CSV column header name
- **path**: JSONPath to canonical model field (e.g., "invoice.invoice_number", "totals.cgst.amount")
- **transform**: Optional transformation (e.g., "date:DD-MM-YYYY", "number:2", "currency:₹")

### Path Examples

- `invoice.invoice_number` - Invoice number
- `invoice.invoice_date` - Invoice date
- `seller.name` - Seller/vendor name
- `buyer.name` - Buyer/customer name
- `buyer.tax_id` - Buyer GSTIN
- `totals.taxable_value` - Total taxable value
- `totals.cgst.amount` - Total CGST amount
- `totals.sgst.amount` - Total SGST amount
- `totals.igst.amount` - Total IGST amount
- `totals.total` - Grand total
- `description` - Line item description (when repeat="line_items")
- `hsn` - HSN code (when repeat="line_items")
- `quantity` - Line item quantity (when repeat="line_items")
- `taxable_value` - Line item taxable value (when repeat="line_items")
- `taxes.cgst.amount` - Line item CGST amount (when repeat="line_items")

## Creating Custom Templates

1. Copy an existing template as a starting point
2. Modify the `columns` array to match your needs
3. Set `repeat` to `"line_items"` for line item export, or `null` for invoice-level
4. Use JSONPath syntax for `path` to reference canonical model fields
5. Add transforms as needed

## Transforms

- `date:DD-MM-YYYY` - Format date (DD-MM-YYYY, MM/DD/YYYY, etc.)
- `number:2` - Format number with 2 decimal places
- `currency:₹` - Format as currency with symbol
