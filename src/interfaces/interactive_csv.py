"""
Interactive CSV creator that maps extracted data to user-defined columns.
"""
import os
import sys
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

from ..core.extraction.document_processor import DocumentProcessor
from ..core.mapping.csv_mapper import CSVMapper


class InteractiveCSVCreator:
    """Interactive tool for creating CSV from document extraction."""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        """Initialize the interactive CSV creator."""
        self.processor = DocumentProcessor(aws_region=aws_region)
        self.mapper = CSVMapper()
    
    def process_document_to_csv(self, file_path: str, output_dir: str = "output") -> str:
        """
        Complete workflow: extract data and create CSV with user-defined columns.
        
        Args:
            file_path: Path to input document
            output_dir: Directory for output files
            
        Returns:
            Path to created CSV file
        """
        print("🚀 Starting Document to CSV Conversion")
        print("=" * 60)
        
        # Step 1: Extract data from document
        print("📄 Step 1: Extracting data from document...")
        results = self.processor.process_document(file_path, output_dir)
        
        # Step 2: Analyze extracted data
        print("\n🔍 Step 2: Analyzing extracted data...")
        categorized_data = self.mapper.analyze_extracted_data(results)
        
        # Show what was found
        self._show_extraction_summary(results, categorized_data)
        
        # Step 3: Get user column preferences
        print("\n📋 Step 3: Define your CSV columns...")
        columns = self.mapper.get_user_columns()
        
        # Step 4: Map data to columns
        print(f"\n🎯 Step 4: Mapping data to {len(columns)} columns...")
        mappings = self.mapper.map_columns_to_data(columns, categorized_data)
        
        # Step 5: Show mapping summary
        self.mapper.print_mapping_summary(columns, mappings)
        
        # Step 6: Create CSV file
        print("\n💾 Step 5: Creating CSV file...")
        csv_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_mapped.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        final_csv_path = self.mapper.create_csv_output(columns, mappings, csv_path)
        
        print(f"✅ CSV file created: {final_csv_path}")
        
        # Step 7: Show final summary
        self._show_final_summary(final_csv_path, columns, mappings)
        
        return final_csv_path
    
    def _show_extraction_summary(self, results: dict, categorized_data: dict):
        """Show summary of what was extracted."""
        print("\n📊 Extraction Summary:")
        print(f"   • {results['summary']['pages']} page(s)")
        print(f"   • {results['summary']['lines']} text lines")
        print(f"   • {results['summary']['words']} words")
        print(f"   • {results['summary']['key_value_pairs']} key-value pairs")
        print(f"   • {results['summary']['tables']} table(s)")
        
        # Show sample data found
        print("\n🔍 Sample data found:")
        sample_categories = ['amounts', 'dates', 'serial_numbers', 'company_names']
        for category in sample_categories:
            if category in categorized_data and categorized_data[category]:
                values = categorized_data[category][:3]  # Show first 3
                print(f"   • {category.replace('_', ' ').title()}: {', '.join(values)}")
    
    def _show_final_summary(self, csv_path: str, columns: list, mappings: dict):
        """Show final summary and next steps."""
        print("\n" + "🎉" + "=" * 58 + "🎉")
        print("SUCCESS! Your CSV file has been created!")
        print("=" * 60)
        
        # Count total data points
        total_values = sum(len(values) for values in mappings.values())
        filled_columns = sum(1 for values in mappings.values() if values)
        
        print(f"📁 File: {csv_path}")
        print(f"📊 Columns: {len(columns)} ({filled_columns} with data)")
        print(f"📈 Data points: {total_values}")
        
        # Show column status
        print(f"\n📋 Column Status:")
        for column in columns:
            values = mappings.get(column, [])
            if values:
                print(f"   ✅ {column}: {len(values)} values")
            else:
                print(f"   ❌ {column}: No data found")
        
        print(f"\n💡 Next Steps:")
        print(f"   1. Open {csv_path} in Excel or any spreadsheet app")
        print(f"   2. Review and edit the mapped data as needed")
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
        print("Usage: python -m src.interactive_csv <document_file>")
        print("\nThis tool will:")
        print("1. Extract data from your document using AWS Textract")
        print("2. Ask you to define CSV column names")
        print("3. Intelligently map extracted data to your columns")
        print("4. Create a CSV file with your structured data")
        print("\nExample: python -m src.interactive_csv invoice.pdf")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        # Create interactive CSV creator
        creator = InteractiveCSVCreator()
        
        # Process document and create CSV
        csv_path = creator.process_document_to_csv(file_path)
        
        print(f"\n🎯 All done! Your CSV is ready at: {csv_path}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()