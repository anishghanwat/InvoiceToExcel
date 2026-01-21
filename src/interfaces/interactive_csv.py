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

from typing import List, Dict, Any, Optional
from ..core.pipeline import InvoiceProcessingPipeline
from ..core.templates.template_parser import TemplateParser


class InteractiveCSVCreator:
    """Interactive tool for creating CSV from invoices using templates."""
    
    def __init__(self, use_ai: bool = True):
        """Initialize the interactive CSV creator."""
        self.pipeline = InvoiceProcessingPipeline(use_ai=use_ai)
        self.template_parser = TemplateParser()
    
    def process_document_to_csv(self, file_path: str, template: Optional[Dict[str, Any]] = None, output_dir: str = "final_output") -> str:
        """
        Complete workflow: extract data and create CSV with user-defined template.
        
        Args:
            file_path: Path to input document
            template: Optional template dict (if None, will use default)
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
        
        # Step 2: Use provided template or use default
        if template is None:
            print("\n📋 Step 2: Using default template...")
            template = self.template_parser.create_default_template()
        else:
            print("\n📋 Step 2: Using provided template...")
        
        # Step 3: Export using template
        print(f"\n💾 Step 3: Exporting CSV with template...")
        from pathlib import Path
        # Ensure final_output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
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
    
    def process_bulk_files(
        self,
        file_paths: List[str],
        template: Dict[str, Any],
        output_dir: str = "final_output"
    ) -> List[str]:
        """
        Process multiple files with the same template.
        
        Args:
            file_paths: List of file paths to process
            template: Template to use for all files
            output_dir: Directory for output files
            
        Returns:
            List of created CSV file paths
        """
        from src.core.bulk_processor import BulkInvoiceProcessor
        
        print("🚀 Starting Bulk Invoice Processing")
        print("=" * 60)
        print(f"📋 Template: {template.get('name', 'Custom Template')}")
        print(f"📁 Files to process: {len(file_paths)}")
        print("=" * 60)
        
        # Ensure final_output directory exists
        from pathlib import Path
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        bulk_processor = BulkInvoiceProcessor(use_ai=True, enable_logging=True)
        
        results = bulk_processor.process_file_list(
            file_paths=file_paths,
            template=template,
            output_format="csv",
            output_dir=output_dir,
            consolidated_output=True
        )
        
        successful_files = [r.get('output_file') for r in results.get('results', []) if r.get('success')]
        
        print("\n" + "=" * 60)
        print("🎉 Bulk Processing Complete!")
        print("=" * 60)
        print(f"✅ Successful: {results.get('successful', 0)}")
        print(f"❌ Failed: {results.get('failed', 0)}")
        if results.get('consolidated_output'):
            print(f"📊 Consolidated output: {results.get('consolidated_output')}")
        print("=" * 60)
        
        return successful_files
    
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
    """Main function for interactive CSV creation with new user flow."""
    import sys
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load environment variables
    load_dotenv()
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Error: AWS credentials not found!")
        print("Please set up your .env file with AWS credentials.")
        sys.exit(1)
    
    try:
        # Create interactive CSV creator
        creator = InteractiveCSVCreator()
        
        # Step 1: Get template file path
        print("🚀 Invoice to CSV Conversion - New Workflow")
        print("=" * 60)
        print("\n📋 Step 1: Template Configuration")
        print("-" * 60)
        
        template_path = input("Enter path to template file (or press Enter to use default template): ").strip()
        template = None
        is_csv_template = template_path.lower().endswith('.csv') if template_path else False
        
        if template_path:
            # Load template from file
            if not os.path.exists(template_path):
                print(f"⚠️  Template file not found: {template_path}")
                print("Will use default template instead.")
                template = creator.template_parser.create_default_template()
            else:
                try:
                    # For CSV templates, we'll process a sample first for better AI mapping
                    if is_csv_template:
                        print("📊 CSV template detected - will process sample invoice first for intelligent mapping...")
                    else:
                        template = creator.template_parser.parse_from_file(template_path)
                        print(f"✅ Loaded template: {template.get('name', 'Custom Template')}")
                except Exception as e:
                    print(f"⚠️  Failed to load template: {e}")
                    print("Will use default template instead.")
                    template = creator.template_parser.create_default_template()
        else:
            # Use default template
            print("Using default template...")
            template = creator.template_parser.create_default_template()
        
        # Step 2: Get file paths (single or bulk)
        print("\n📁 Step 2: File Selection")
        print("-" * 60)
        print("Enter file paths (one per line, or comma-separated).")
        print("Press Enter twice when done, or type 'done' to finish.")
        
        file_paths = []
        print("\nEnter file path(s):")
        while True:
            line = input().strip()
            if not line or line.lower() == 'done':
                break
            
            # Handle comma-separated paths
            paths = [p.strip() for p in line.split(',')]
            for path in paths:
                if path:
                    if os.path.exists(path):
                        file_paths.append(path)
                        print(f"  ✅ Added: {path}")
                    else:
                        print(f"  ⚠️  File not found: {path}")
        
        if not file_paths:
            print("❌ Error: No valid file paths provided!")
            sys.exit(1)
        
        # Step 3: For CSV templates, process sample first for better AI mapping
        if is_csv_template and template_path and template is None:
            print(f"\n🔍 Step 3a: Processing sample invoice for intelligent header mapping...")
            print("=" * 60)
            try:
                # Process first file to get canonical sample
                sample_result = creator.pipeline.process_invoice(file_paths[0], output_format="json")
                canonical_sample = sample_result.get('canonical', {})
                
                # Now parse template with sample for better AI mapping
                template = creator.template_parser.parse_from_file(
                    template_path,
                    canonical_sample=canonical_sample,
                    use_ai_mapping=True
                )
                print(f"✅ Template mapped with AI using sample data: {template.get('name', 'Custom Template')}")
                print(f"📋 Mapped {len(template.get('columns', []))} columns")
            except Exception as e:
                print(f"⚠️  Sample processing failed: {e}")
                print("Falling back to keyword-based mapping...")
                try:
                    template = creator.template_parser.parse_from_file(template_path, use_ai_mapping=False)
                except Exception as e2:
                    print(f"⚠️  Template loading failed: {e2}")
                    template = creator.template_parser.create_default_template()
        
        # Step 3/4: Process files
        print(f"\n🔄 Step {'3b' if is_csv_template and template_path else '3'}: Processing {len(file_paths)} file(s)...")
        print("=" * 60)
        
        if len(file_paths) == 1:
            # Single file processing
            csv_path = creator.process_document_to_csv(file_paths[0], template=template)
            print(f"\n🎯 All done! Your CSV is ready at: {csv_path}")
        else:
            # Bulk processing
            csv_paths = creator.process_bulk_files(file_paths, template)
            print(f"\n🎯 All done! Processed {len(csv_paths)} file(s)")
        
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