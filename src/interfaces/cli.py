"""
Command line interface for invoice processing using the new architecture.

This CLI uses the InvoiceProcessingPipeline which follows the finance-grade
extraction-only approach: Extract truth, not columns.
"""
import sys
import os
import argparse
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

from dotenv import load_dotenv
from ..core.pipeline import InvoiceProcessingPipeline
from ..core.templates.template_parser import TemplateParser


def main():
    """Main CLI function."""
    # Load environment variables
    load_dotenv()
    
    # Check for required AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Error: AWS credentials not found!")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        print("or create a .env file with your credentials.")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Process invoices using finance-grade extraction pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process invoice with default template
  python -m src.interfaces.cli invoice.pdf
  
  # Process with specific template
  python -m src.interfaces.cli invoice.pdf --template templates/gstr1.json
  
  # Export to JSON instead of CSV
  python -m src.interfaces.cli invoice.pdf --format json
  
  # Disable AI fixing
  python -m src.interfaces.cli invoice.pdf --no-ai
        """
    )
    parser.add_argument('file_path', help='Path to invoice file (PDF, PNG, JPG, JPEG)')
    parser.add_argument('--template', '-t', help='Path to template JSON file (default: uses simple invoice template)')
    parser.add_argument('--format', '-f', choices=['csv', 'json', 'excel'], default='csv',
                       help='Output format (default: csv)')
    parser.add_argument('--output', '-o', help='Output file path (default: auto-generated)')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI fixing (extraction only)')
    
    args = parser.parse_args()
    
    file_path = args.file_path
    
    # Validate file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    try:
        # Initialize pipeline
        pipeline = InvoiceProcessingPipeline(use_ai=not args.no_ai)
        template_parser = TemplateParser()
        
        # Load template if provided
        template = None
        if args.template:
            if not os.path.exists(args.template):
                print(f"❌ Error: Template file not found: {args.template}")
                sys.exit(1)
            template = template_parser.parse_from_file(args.template)
            print(f"📋 Using template: {template.get('name', 'Custom Template')}")
        
        # Process invoice
        print(f"\n🔄 Processing invoice: {os.path.basename(file_path)}")
        print("=" * 60)
        
        result = pipeline.process_invoice(
            file_path=file_path,
            template=template,
            output_format=args.format,
            output_path=args.output
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ Processing complete!")
        print("=" * 60)
        
        if result.get('output_file'):
            print(f"📄 Output file: {result['output_file']}")
        
        if result.get('canonical'):
            canonical = result['canonical']
            invoice = canonical.get('invoice', {})
            totals = canonical.get('totals', {})
            
            print(f"\n📊 Invoice Summary:")
            print(f"   Invoice #: {invoice.get('invoice_number', 'N/A')}")
            print(f"   Date: {invoice.get('invoice_date', 'N/A')}")
            print(f"   Seller: {canonical.get('seller', {}).get('name', 'N/A')}")
            print(f"   Buyer: {canonical.get('buyer', {}).get('name', 'N/A')}")
            print(f"   Line Items: {len(canonical.get('line_items', []))}")
            print(f"   Total: {totals.get('total', 'N/A')}")
        
        if result.get('validation'):
            validation = result['validation']
            if validation.get('valid'):
                print(f"\n✅ Validation: Passed")
            else:
                print(f"\n⚠️  Validation: {len(validation.get('errors', []))} errors found")
        
        print(f"\n💡 Tip: Check the 'output' directory for all generated files.")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        if os.getenv('DEBUG'):
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()