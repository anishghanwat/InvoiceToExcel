"""
Batch CSV generator - Automatically creates CSV files for all extracted documents
using common default columns.
"""
import os
import sys
import json
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to Python path
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

from src.core.mapping.csv_mapper import CSVMapper
from src.core.mapping.professional_csv_mapper import ProfessionalCSVMapper


def get_default_columns():
    """Get default column names for invoices."""
    return [
        "sr.no",
        "particulars",
        "description",
        "qty",
        "rate",
        "amount",
        "date",
        "invoice_no",
        "total",
        "tax"
    ]


def process_all_results(output_dir="output"):
    """Process all result JSON files and create CSV files."""
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"❌ Output directory '{output_dir}' does not exist!")
        return
    
    # Find all result JSON files
    result_files = list(output_path.glob("*_results.json"))
    
    if not result_files:
        print(f"❌ No result files found in '{output_dir}' directory!")
        print("   Please run extraction first using: python main.py cli <document>")
        return
    
    print(f"📊 Found {len(result_files)} result file(s) to process")
    print("=" * 60)
    
    # Use professional mapper for audit-ready CSVs
    professional_mapper = ProfessionalCSVMapper()
    standard_mapper = CSVMapper()
    default_columns = get_default_columns()
    
    success_count = 0
    error_count = 0
    
    for result_file in result_files:
        try:
            # Load results
            print(f"\n📄 Processing: {result_file.name}")
            with open(result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Extract professional invoice structure
            print(f"   Extracting invoice structure...")
            invoice_structure = professional_mapper.extract_invoice_structure(results)
            
            # Create professional CSV
            csv_filename = result_file.name.replace("_results.json", "_professional.csv")
            csv_path = output_path / csv_filename
            
            # Create both formats
            professional_mapper.create_professional_csv(invoice_structure, str(csv_path), include_header=True)
            
            # Also create flat format (standard accounting format)
            flat_csv_filename = result_file.name.replace("_results.json", "_flat.csv")
            flat_csv_path = output_path / flat_csv_filename
            professional_mapper.create_flat_csv(invoice_structure, str(flat_csv_path))
            
            # Count line items
            line_items_count = len(invoice_structure.get('line_items', []))
            header_fields = len(invoice_structure.get('header', {}))
            
            print(f"   ✅ Created professional CSV: {csv_filename}")
            print(f"      Invoice header fields: {header_fields}")
            print(f"      Line items: {line_items_count}")
            print(f"      Ready for audit/accounting use")
            
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error processing {result_file.name}: {str(e)}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Batch processing complete!")
    print(f"   Success: {success_count} file(s)")
    if error_count > 0:
        print(f"   Errors: {error_count} file(s)")
    print("=" * 60)


if __name__ == '__main__':
    process_all_results()
