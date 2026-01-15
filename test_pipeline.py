"""
Test script for the new invoice processing pipeline.

Tests the complete flow:
Textract → Canonical Model → AI Fix → Validation → Template Export
"""
import sys
import os
import json
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser

# Load environment variables
load_dotenv()


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_canonical_summary(canonical: dict):
    """Print a summary of the canonical model."""
    print_section("Canonical Invoice Model Summary")
    
    invoice = canonical.get("invoice", {})
    seller = canonical.get("seller", {})
    buyer = canonical.get("buyer", {})
    totals = canonical.get("totals", {})
    line_items = canonical.get("line_items", [])
    metadata = canonical.get("metadata", {})
    
    print("\n📋 Invoice Information:")
    print(f"   Invoice Number: {invoice.get('invoice_number', 'N/A')}")
    print(f"   Invoice Date: {invoice.get('invoice_date', 'N/A')}")
    print(f"   Due Date: {invoice.get('due_date', 'N/A')}")
    print(f"   Order Number: {invoice.get('order_number', 'N/A')}")
    
    print("\n🏢 Seller/Vendor:")
    print(f"   Name: {seller.get('name', 'N/A')}")
    print(f"   Tax ID: {seller.get('tax_id', 'N/A')}")
    address = seller.get('address', {})
    if address.get('line1'):
        print(f"   Address: {address.get('line1', '')}")
    
    print("\n👤 Buyer/Customer:")
    print(f"   Name: {buyer.get('name', 'N/A')}")
    print(f"   Tax ID: {buyer.get('tax_id', 'N/A')}")
    
    print("\n💰 Totals:")
    print(f"   Taxable Value: {totals.get('taxable_value', 'N/A')}")
    print(f"   Currency: {totals.get('currency', 'N/A')}")
    
    # Tax breakdown
    cgst = totals.get('cgst', {})
    sgst = totals.get('sgst', {})
    igst = totals.get('igst', {})
    
    if cgst.get('amount'):
        print(f"   CGST: {cgst.get('amount')} (Rate: {cgst.get('rate', 'N/A')}%)")
    if sgst.get('amount'):
        print(f"   SGST: {sgst.get('amount')} (Rate: {sgst.get('rate', 'N/A')}%)")
    if igst.get('amount'):
        print(f"   IGST: {igst.get('amount')} (Rate: {igst.get('rate', 'N/A')}%)")
    
    print(f"   Total: {totals.get('total', 'N/A')}")
    
    print(f"\n📦 Line Items: {len(line_items)} items")
    for i, item in enumerate(line_items[:3], 1):  # Show first 3
        print(f"   {i}. {item.get('description', 'N/A')[:50]}")
        if item.get('taxable_value'):
            print(f"      Taxable: {item.get('taxable_value')}, Total: {item.get('total', 'N/A')}")
    
    if len(line_items) > 3:
        print(f"   ... and {len(line_items) - 3} more items")
    
    print(f"\n📊 Metadata:")
    confidence = metadata.get('confidence', {})
    print(f"   Overall Confidence: {confidence.get('overall', 0):.2%}")
    print(f"   Processing Time: {metadata.get('processing_time_ms', 0)}ms")


def print_validation_results(validation: dict):
    """Print validation results."""
    print_section("Validation Results")
    
    if validation.get("valid"):
        print("✅ Validation PASSED - All checks passed!")
    else:
        print("❌ Validation FAILED - Issues found:")
    
    errors = validation.get("errors", [])
    warnings = validation.get("warnings", [])
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for error in errors:
            print(f"   • {error}")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not errors and not warnings:
        print("\n✅ No errors or warnings!")


def main():
    """Main test function."""
    print_section("Invoice Processing Pipeline Test")
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Error: AWS credentials not found!")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        print("or create a .env file with your credentials.")
        return
    
    # Select a sample invoice
    sample_dir = Path("samples")
    if not sample_dir.exists():
        print(f"❌ Error: Samples directory not found: {sample_dir}")
        return
    
    # Try to find a sample invoice
    sample_files = list(sample_dir.glob("*.pdf")) + list(sample_dir.glob("*.png")) + list(sample_dir.glob("*.jpg"))
    
    if not sample_files:
        print(f"❌ Error: No sample invoices found in {sample_dir}")
        return
    
    # Use the first available sample
    sample_file = sample_files[0]
    print(f"\n📄 Using sample invoice: {sample_file.name}")
    print(f"   Path: {sample_file}")
    
    try:
        # Initialize pipeline
        print("\n🚀 Initializing pipeline...")
        use_ai = os.getenv('GEMINI_API_KEY') is not None
        if not use_ai:
            print("   ⚠️  AI disabled (GEMINI_API_KEY not found)")
        else:
            print("   ✅ AI enabled")
        
        pipeline = InvoiceProcessingPipeline(use_ai=use_ai)
        
        # Process invoice
        print(f"\n🔄 Processing invoice...")
        result = pipeline.process_invoice(
            file_path=str(sample_file),
            template=None,  # Use default template
            output_format="csv",
            output_path=None  # Auto-generate path
        )
        
        # Print results
        print_canonical_summary(result["canonical"])
        print_validation_results(result["validation"])
        
        # Show output files
        print_section("Output Files")
        if result.get("output_file"):
            print(f"✅ CSV Export: {result['output_file']}")
            
            # Also export canonical JSON
            from src.core.templates.exporter import TemplateExporter
            exporter = TemplateExporter()
            json_path = result["output_file"].replace(".csv", "_canonical.json")
            exporter.export_to_json(result["canonical"], json_path)
            print(f"✅ Canonical JSON: {json_path}")
        
        # Test with line items template
        print_section("Testing Line Items Template")
        template_parser = TemplateParser()
        line_items_template = template_parser.create_line_items_template()
        
        line_items_path = result["output_file"].replace(".csv", "_line_items.csv")
        exporter = TemplateExporter()
        exporter.export_to_csv(result["canonical"], line_items_template, line_items_path)
        print(f"✅ Line Items CSV: {line_items_path}")
        
        print_section("Test Complete")
        print("✅ Pipeline test completed successfully!")
        print(f"\n📁 Check the 'output' directory for all generated files:")
        print(f"   - CSV export (invoice-level)")
        print(f"   - Line items CSV (item-level)")
        print(f"   - Canonical JSON (full model)")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
