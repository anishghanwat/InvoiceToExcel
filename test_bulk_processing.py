"""
Test script for bulk invoice processing.
"""
import sys
from pathlib import Path
from src.core.bulk_processor import BulkInvoiceProcessor
from src.core.templates.template_parser import TemplateParser


def test_bulk_processing():
    """Test bulk processing with sample invoices."""
    print("=" * 70)
    print("BULK PROCESSING TEST")
    print("=" * 70)
    
    # Check for sample invoices
    samples_dir = Path("samples")
    if not samples_dir.exists():
        print("❌ Samples directory not found")
        return False
    
    sample_files = list(samples_dir.glob("*.pdf")) + list(samples_dir.glob("*.png"))
    if not sample_files:
        print("❌ No sample invoices found")
        return False
    
    print(f"📁 Found {len(sample_files)} sample invoice(s)")
    
    # Initialize processor
    processor = BulkInvoiceProcessor(
        max_workers=2,  # Use 2 workers for testing
        use_ai=False,  # Disable AI for faster testing
        enable_logging=True
    )
    
    # Load template
    template_parser = TemplateParser()
    template = template_parser.parse_from_file("templates/invoice_summary.json")
    
    # Process files
    print("\n🚀 Starting bulk processing...\n")
    summary = processor.process_file_list(
        file_paths=[str(f) for f in sample_files[:3]],  # Limit to 3 for testing
        template=template,
        output_format="csv",
        output_dir="output",
        consolidated_output=True,
        progress_callback=lambda current, total, filename: None  # Silent for test
    )
    
    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total: {summary['total']}")
    print(f"Processed: {summary['processed']}")
    print(f"✅ Successful: {summary['successful']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"⏱️  Time: {summary['processing_time_seconds']:.2f}s")
    print(f"📊 Avg per invoice: {summary['average_time_per_invoice']:.2f}s")
    
    if summary.get('consolidated_output'):
        print(f"\n📦 Consolidated file: {summary['consolidated_output']}")
    
    # Check for failures
    failed = [r for r in summary['results'] if not r.get('success')]
    if failed:
        print(f"\n⚠️  {len(failed)} file(s) failed:")
        for result in failed:
            print(f"   - {Path(result['file']).name}: {result.get('error', 'Unknown')}")
    
    return summary['failed'] == 0


if __name__ == '__main__':
    success = test_bulk_processing()
    sys.exit(0 if success else 1)
