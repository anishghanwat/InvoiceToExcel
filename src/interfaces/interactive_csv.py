"""
Interactive CSV creator using the new template-based architecture.

This interface uses the InvoiceProcessingPipeline with user-defined templates
for flexible, finance-grade invoice processing.
"""
import os
import sys
import json
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

from ..core.pipeline import InvoiceProcessingPipeline
from ..core.templates.template_parser import TemplateParser


class InteractiveCSVCreator:
    """Interactive tool for creating CSV from invoices using templates."""
    
    def __init__(self, use_ai: bool = True):
        """Initialize the interactive CSV creator."""
        self.pipeline = InvoiceProcessingPipeline(use_ai=use_ai)
        self.template_parser = TemplateParser()
    
    def process_document_to_csv(self, file_path: str, output_dir: str = "output") -> str:
        """
        Complete workflow: extract data and create CSV with user-defined template.
        
        Args:
            file_path: Path to input document
            output_dir: Directory for output files
            
        Returns:
            Path to created CSV file
        """
        print("🚀 Starting Invoice to CSV Conversion")
        print("=" * 60)
        
        # Step 1: Process invoice to get canonical model
        print("📄 Step 1: Processing invoice...")
        result = self.pipeline.process_invoice(file_path, output_format="json")
        
        canonical = result.get('canonical', {})
        
        # Show what was extracted
        self._show_extraction_summary(canonical)
        
        # Step 2: Let user choose or create template
        print("\n📋 Step 2: Choose template or create custom...")
        template = self._get_user_template()
        
        # Step 3: Export using template
        print(f"\n💾 Step 3: Exporting CSV with template...")
        from pathlib import Path
        input_path = Path(file_path)
        csv_filename = f"{input_path.stem}_export.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        # Export with template
        result = self.pipeline.process_invoice(
            file_path=file_path,
            template=template,
            output_format="csv",
            output_path=csv_path
        )
        
        final_csv_path = result.get('output_file', csv_path)
        
        print(f"✅ CSV file created: {final_csv_path}")
        
        # Step 4: Show final summary
        self._show_final_summary(final_csv_path, template, canonical)
        
        return final_csv_path
    
    def _show_extraction_summary(self, canonical: dict):
        """Show summary of what was extracted."""
        print("\n📊 Extraction Summary:")
        
        invoice = canonical.get('invoice', {})
        seller = canonical.get('seller', {})
        buyer = canonical.get('buyer', {})
        line_items = canonical.get('line_items', [])
        totals = canonical.get('totals', {})
        
        print(f"   Invoice #: {invoice.get('invoice_number', 'N/A')}")
        print(f"   Date: {invoice.get('invoice_date', 'N/A')}")
        print(f"   Seller: {seller.get('name', 'N/A')}")
        print(f"   Buyer: {buyer.get('name', 'N/A')}")
        print(f"   Line Items: {len(line_items)}")
        print(f"   Taxable Value: {totals.get('taxable_value', 'N/A')}")
        print(f"   Total: {totals.get('total', 'N/A')}")
        
        if line_items:
            print(f"\n📦 Line Items Preview:")
            for i, item in enumerate(line_items[:3], 1):  # Show first 3
                desc = item.get('description', 'N/A')[:50]
                print(f"   {i}. {desc}...")
            if len(line_items) > 3:
                print(f"   ... and {len(line_items) - 3} more")
    
    def _get_user_template(self) -> dict:
        """Get template from user (choose existing or create custom)."""
        # Show available default templates
        default_templates = {
            '1': ('Simple Invoice', 'simple_invoice'),
            '2': ('GSTR-1 Export', 'gstr1'),
            '3': ('Tally Import', 'tally'),
            '4': ('QuickBooks', 'quickbooks'),
            '5': ('Xero', 'xero'),
            '6': ('Audit Trail', 'audit_trail'),
        }
        
        print("\nAvailable Templates:")
        for key, (name, _) in default_templates.items():
            print(f"   {key}. {name}")
        print("   7. Create custom template")
        
        choice = input("\nSelect template (1-7): ").strip()
        
        if choice in default_templates:
            template_name = default_templates[choice][1]
            template_path = f"templates/{template_name}.json"
            if os.path.exists(template_path):
                return self.template_parser.parse_from_file(template_path)
            else:
                print(f"⚠️  Template file not found: {template_path}")
                print("Using default template instead.")
                return self.template_parser.create_default_template()
        elif choice == '7':
            return self._create_custom_template()
        else:
            print("⚠️  Invalid choice. Using default template.")
            return self.template_parser.create_default_template()
    
    def _create_custom_template(self) -> dict:
        """Create a custom template interactively."""
        print("\n📝 Creating Custom Template")
        print("=" * 60)
        
        template_name = input("Template name: ").strip() or "Custom Template"
        
        # Ask if line items should be expanded
        repeat_choice = input("Export line items? (y/n): ").strip().lower()
        repeat = "line_items" if repeat_choice == 'y' else None
        
        # Get columns
        print("\nEnter column definitions (press Enter with empty name to finish):")
        columns = []
        while True:
            header = input(f"\nColumn {len(columns) + 1} header: ").strip()
            if not header:
                break
            
            print("Available paths (examples):")
            print("  - invoice.invoice_number")
            print("  - invoice.invoice_date")
            print("  - seller.name")
            print("  - buyer.name")
            print("  - totals.taxable_value")
            print("  - totals.cgst.amount")
            print("  - totals.sgst.amount")
            print("  - totals.total")
            if repeat:
                print("  - description (line item)")
                print("  - hsn (line item)")
                print("  - quantity (line item)")
                print("  - taxable_value (line item)")
            
            path = input("  Path: ").strip()
            if not path:
                print("⚠️  Path required. Skipping column.")
                continue
            
            transform = input("  Transform (optional, e.g., 'number:2', 'date:DD-MM-YYYY'): ").strip() or None
            
            col_def = {"header": header, "path": path}
            if transform:
                col_def["transform"] = transform
            
            columns.append(col_def)
            print(f"✅ Added column: {header}")
        
        if not columns:
            print("⚠️  No columns defined. Using default template.")
            return self.template_parser.create_default_template()
        
        template = {
            "name": template_name,
            "description": f"Custom template created interactively",
            "columns": columns
        }
        
        if repeat:
            template["repeat"] = repeat
        
        print(f"\n✅ Custom template created with {len(columns)} columns")
        return template
    
    def _show_final_summary(self, csv_path: str, template: dict, canonical: dict):
        """Show final summary and next steps."""
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Your CSV file has been created!")
        print("=" * 60)
        
        columns = template.get('columns', [])
        line_items = canonical.get('line_items', [])
        
        if template.get('repeat') == 'line_items':
            num_rows = len(line_items)
        else:
            num_rows = 1
        
        print(f"📁 File: {csv_path}")
        print(f"📋 Template: {template.get('name', 'Custom')}")
        print(f"📊 Columns: {len(columns)}")
        print(f"📈 Rows: {num_rows}")
        
        print(f"\n💡 Next Steps:")
        print(f"   1. Open {csv_path} in Excel or any spreadsheet app")
        print(f"   2. Review the extracted data")
        print(f"   3. Use the CSV for your accounting or data processing")
        
        print("=" * 60)


def main():
    """Main function for interactive CSV creation."""
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Error: AWS credentials not found!")
        print("Please set up your .env file with AWS credentials.")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python -m src.interfaces.interactive_csv <invoice_file>")
        print("\nThis tool will:")
        print("1. Extract data from your invoice using AWS Textract")
        print("2. Build a canonical invoice model (finance-grade extraction)")
        print("3. Let you choose or create a template for CSV export")
        print("4. Create a CSV file with your structured data")
        print("\nExample: python -m src.interfaces.interactive_csv invoice.pdf")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Validate file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    try:
        # Create interactive CSV creator
        creator = InteractiveCSVCreator()
        
        # Process document and create CSV
        csv_path = creator.process_document_to_csv(file_path)
        
        print(f"\n🎯 All done! Your CSV is ready at: {csv_path}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        if os.getenv('DEBUG'):
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()