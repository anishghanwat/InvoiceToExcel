"""
Test script to verify CSV export accuracy with AI mapping.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from dotenv import load_dotenv
load_dotenv()

from src.core.templates.template_parser import TemplateParser
from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.exporter import TemplateExporter

def test_export_accuracy():
    """Test CSV export with AI-mapped template."""
    print("Testing CSV Export Accuracy with AI Mapping")
    print("=" * 60)
    
    # Step 1: Process invoice
    print("\nStep 1: Processing invoice...")
    pipeline = InvoiceProcessingPipeline(use_ai=True)
    
    sample_file = "gstpendinginvoices/MMFPL-45-2025-26.pdf"
    result = pipeline.process_invoice(sample_file, output_format="json")
    canonical = result.get('canonical', {})
    
    print(f"Invoice: {canonical.get('invoice', {}).get('invoice_number', 'N/A')}")
    
    # Check what data we have
    line_items = canonical.get('line_items', [])
    if line_items:
        first_item = line_items[0]
        print(f"\nLine Item Data:")
        print(f"  Description: {first_item.get('description', 'N/A')}")
        print(f"  Unit Price: {first_item.get('unit_price', 'N/A')}")
        print(f"  Taxable Value: {first_item.get('taxable_value', 'N/A')}")
    
    totals = canonical.get('totals', {})
    print(f"\nTotals:")
    print(f"  Taxable Value: {totals.get('taxable_value', 'N/A')}")
    print(f"  Round Off: {totals.get('round_off', 'N/A')}")
    print(f"  Total: {totals.get('total', 'N/A')}")
    
    metadata = canonical.get('metadata', {})
    print(f"\nMetadata:")
    print(f"  Ledger: {metadata.get('ledger', 'N/A')}")
    
    # Step 2: Parse template with AI mapping
    print("\nStep 2: Parsing template with AI mapping...")
    template_path = "ExampleTempates/final_output.csv"
    parser = TemplateParser()
    
    template = parser.parse_from_file(
        template_path,
        canonical_sample=canonical,
        use_ai_mapping=True
    )
    
    print(f"Template: {template.get('name', 'N/A')}")
    print(f"Columns: {len(template.get('columns', []))}")
    
    # Step 3: Export CSV
    print("\nStep 3: Exporting CSV...")
    exporter = TemplateExporter()
    output_path = "final_output/test_export.csv"
    
    csv_path = exporter.export_to_csv(canonical, template, output_path)
    print(f"Exported to: {csv_path}")
    
    # Step 4: Read and display CSV
    print("\nStep 4: Verifying exported CSV...")
    import csv
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        if rows:
            print("\nHeaders:", rows[0])
            if len(rows) > 1:
                print("Data Row:", rows[1])
                
                # Check which fields are empty
                print("\nField Analysis:")
                for i, header in enumerate(rows[0]):
                    value = rows[1][i] if len(rows[1]) > i else ""
                    status = "FILLED" if value.strip() else "EMPTY"
                    print(f"  {header:20} = {value[:30]:30} [{status}]")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == '__main__':
    test_export_accuracy()
