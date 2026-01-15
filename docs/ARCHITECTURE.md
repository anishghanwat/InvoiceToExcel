# Invoice Processing Architecture

## Core Principle (Non-Negotiable)

**Extraction ≠ Output format**

Your app should extract truth, not columns.

Once truth is correct, any template is just a projection.

## Architecture Flow

```
PDF / Image
   ↓
Textract
   ↓
Raw Signals (words, tables, kv)
   ↓
🧠 Canonical Invoice Model  ← accuracy happens here
   ↓
🧩 Template Engine          ← flexibility happens here
   ↓
CSV / Excel / JSON / API
```

## Directory Structure

```
src/core/
├── extraction/          # Textract integration
│   ├── textract_client.py
│   └── document_processor.py
│
├── normalize/           # Canonical model builder
│   ├── canonical_schema.py    # Rich canonical schema
│   └── canonical_builder.py   # Builds canonical JSON from Textract
│
├── ai/                  # AI layer (works ONLY with canonical)
│   └── canonical_fixer.py     # AI fixes canonical JSON
│
├── validators/          # Validation before export
│   ├── gst.py          # GST/GSTIN validation
│   ├── math.py          # Math consistency checks
│   └── validator.py     # Main validation engine
│
├── templates/           # Template engine (flexibility)
│   ├── template_parser.py    # Reads user templates
│   └── exporter.py          # Applies mappings
│
└── pipeline.py         # Main orchestration
```

## Key Components

### 1. Canonical Model (Rich, Not Minimal)

The canonical model is **richer** than any output template. It captures:

- **Detailed tax breakdown**: CGST, SGST, IGST separately (not just "total_tax")
- **Rich addresses**: Line1, Line2, City, State, Postal Code (not just "address")
- **Complete line items**: HSN, quantity, unit, taxes per item
- **Metadata**: Confidence scores, processing time, source

**Why rich?**
- You can collapse rich → simple
- You cannot expand simple → rich
- GSTR-1 needs split taxes
- Some templates need total only
- Some need rate + amount

### 2. Canonical Builder

**Location**: `src/core/normalize/canonical_builder.py`

- **ONLY** builds canonical JSON from Textract output
- **NO CSV logic** here. Ever.
- Extracts truth, not columns

### 3. AI Canonical Fixer

**Location**: `src/core/ai/canonical_fixer.py`

- AI works **ONLY** with canonical JSON
- AI **never** sees CSVs
- Input: Raw Textract + Partial canonical + Validation rules
- Output: Canonical JSON ONLY (strict schema, confidence scores)

**AI instruction (conceptual)**:
> "Fill missing fields in this canonical invoice JSON.
> If a value is not present or cannot be inferred, set it to null.
> Do not invent data."

This gives:
- High accuracy
- Controlled hallucination
- Auditable results

### 4. Template Engine

**Locations**: 
- `src/core/templates/template_parser.py`
- `src/core/templates/exporter.py`

Templates are **pure configuration**, not code.

A template defines:
- Columns
- Mapping rules (JSONPath to canonical model)
- Optional transforms
- Row expansion rules (for line items)

**Example Template**:
```json
{
  "columns": [
    {
      "header": "Invoice No",
      "path": "invoice.invoice_number"
    },
    {
      "header": "Invoice Date",
      "path": "invoice.invoice_date",
      "transform": "date:DD-MM-YYYY"
    },
    {
      "header": "IGST Amount",
      "path": "totals.igst.amount"
    }
  ]
}
```

**Line Items Template**:
```json
{
  "repeat": "line_items",
  "columns": [
    { "header": "Description", "path": "description" },
    { "header": "HSN", "path": "hsn" },
    { "header": "Taxable Value", "path": "taxable_value" }
  ]
}
```

**Features**:
- No AI needed here
- Deterministic
- Fast
- User-controllable

### 5. Validation Engine

**Location**: `src/core/validators/`

Before export, validates:
- ✅ Invoice totals = sum(line items)
- ✅ GSTIN format valid
- ✅ State code matches GSTIN
- ✅ Tax logic consistent (IGST vs CGST/SGST)

If validation fails:
- Flag row
- Allow user correction
- Re-export

## Usage Example

```python
from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser

# Initialize pipeline
pipeline = InvoiceProcessingPipeline(use_ai=True)

# Process invoice (builds canonical model)
result = pipeline.process_invoice(
    file_path="invoice.pdf",
    template=None,  # Uses default template
    output_format="csv",
    output_path="output/invoice.csv"
)

# Access canonical model
canonical = result["canonical"]

# Check validation
validation = result["validation"]
if not validation["valid"]:
    print("Errors:", validation["errors"])

# Use custom template
template_parser = TemplateParser()
custom_template = template_parser.parse_from_file("templates/gstr1.json")

# Export with custom template
from src.core.templates.exporter import TemplateExporter
exporter = TemplateExporter()
exporter.export_to_csv(canonical, custom_template, "output/gstr1.csv")
```

## Why This Beats Competitors

**They are**:
- Column-first
- Template-first
- Fragile

**You are**:
- Data-first
- Schema-first
- Compliance-ready

This lets you say:
> "Upload any invoice. Export to any format. Accuracy guaranteed."

That's a premium product.

## Future Enhancements

This architecture enables:
- User-defined templates (huge differentiator)
- API access
- Compliance exports (GSTR-1, TDS, VAT, EU VAT)
- Confidence scoring
- Review UI
- Enterprise pricing
