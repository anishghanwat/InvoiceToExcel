# Bulk Invoice Processing Guide

## Overview

The bulk processing feature allows you to process multiple invoices in parallel, significantly reducing total processing time.

## Features

- ✅ Parallel processing with configurable workers
- ✅ Progress tracking and reporting
- ✅ Consolidated output (single file with all invoices)
- ✅ Error handling per invoice (one failure doesn't stop others)
- ✅ Skip already processed files
- ✅ Summary statistics

## Usage

### Command Line

#### Process Directory

```bash
# Process all invoices in a directory
python -m src.interfaces.bulk_cli process-dir ./invoices --output-dir ./output

# With specific template
python -m src.interfaces.bulk_cli process-dir ./invoices --template templates/gstr1.json

# With 5 parallel workers
python -m src.interfaces.bulk_cli process-dir ./invoices --workers 5

# Skip files that already have output
python -m src.interfaces.bulk_cli process-dir ./invoices --skip-existing

# Disable AI (faster processing)
python -m src.interfaces.bulk_cli process-dir ./invoices --no-ai
```

#### Process Specific Files

```bash
# Process specific files
python -m src.interfaces.bulk_cli process-files invoice1.pdf invoice2.pdf invoice3.pdf

# With template and custom output
python -m src.interfaces.bulk_cli process-files *.pdf --template templates/tally.json --output-dir ./tally_output
```

#### Using main.py

```bash
# Process directory via main.py
python main.py bulk process-dir ./invoices

# Process files via main.py
python main.py bulk process-files invoice1.pdf invoice2.pdf
```

### Python API

```python
from src.core.bulk_processor import BulkInvoiceProcessor
from src.core.templates.template_parser import TemplateParser

# Initialize processor
processor = BulkInvoiceProcessor(max_workers=5, use_ai=True)

# Load template
template_parser = TemplateParser()
template = template_parser.parse_from_file("templates/invoice_summary.json")

# Process directory
summary = processor.process_directory(
    input_dir="invoices",
    template=template,
    output_format="csv",
    output_dir="output",
    consolidated_output=True,
    skip_existing=False
)

print(f"Processed {summary['successful']}/{summary['total']} invoices")
```

## Performance

### Parallel Processing

- Default: 3 workers (processes 3 invoices simultaneously)
- Recommended: 3-5 workers for optimal performance
- Maximum: Limited by AWS Textract API rate limits

### Processing Time

- Single invoice: ~10-15 seconds
- 10 invoices (3 workers): ~40-50 seconds (vs ~150 seconds sequential)
- 100 invoices (5 workers): ~5-7 minutes (vs ~25 minutes sequential)

## Output

### Individual Files

Each invoice generates its own output file:
- `{filename}_export.csv` - CSV export
- `{filename}_canonical.json` - Full canonical model

### Consolidated Output

A single file containing all invoices:
- `consolidated_invoices.csv` - All invoices in one CSV
- `consolidated_invoices.json` - All invoices in one JSON

## Error Handling

- Individual invoice failures don't stop processing
- Failed files are logged with error details
- Summary report includes success/failure counts

## Configuration

Environment variables:
```bash
BULK_MAX_WORKERS=5              # Number of parallel workers
BULK_CONSOLIDATED_OUTPUT=true   # Create consolidated output
BULK_SKIP_EXISTING=false        # Skip already processed files
```

## Best Practices

1. **Worker Count**: Start with 3 workers, increase if AWS quota allows
2. **Skip Existing**: Use `--skip-existing` for re-runs
3. **Template**: Use consistent templates for consolidated output
4. **Monitoring**: Check logs for failed files
5. **Testing**: Test with small batch first

## Limitations

- AWS Textract API rate limits may require throttling
- Memory usage increases with number of workers
- Consolidated CSV may be large for 1000+ invoices

## Examples

### Example 1: Process All Invoices in Directory

```bash
python -m src.interfaces.bulk_cli process-dir ./invoices \
    --template templates/invoice_summary.json \
    --output-dir ./output \
    --workers 3
```

### Example 2: Process Specific Files with Progress

```python
from src.core.bulk_processor import BulkInvoiceProcessor

def progress_callback(current, total, filename):
    print(f"Processing {current}/{total}: {filename}")

processor = BulkInvoiceProcessor(max_workers=3)
summary = processor.process_file_list(
    file_paths=["invoice1.pdf", "invoice2.pdf", "invoice3.pdf"],
    progress_callback=progress_callback
)
```

### Example 3: Skip Already Processed Files

```bash
# First run - processes all files
python -m src.interfaces.bulk_cli process-dir ./invoices

# Second run - only processes new files
python -m src.interfaces.bulk_cli process-dir ./invoices --skip-existing
```

## Troubleshooting

### Issue: Rate Limit Errors

**Solution**: Reduce number of workers or add delays between requests.

### Issue: Memory Issues

**Solution**: Reduce number of workers or process in smaller batches.

### Issue: Consolidated CSV Too Large

**Solution**: Process in batches or use JSON output format.
