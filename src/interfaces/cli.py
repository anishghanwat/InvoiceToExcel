"""
Command line interface for document processing.
"""
import sys
import os
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
from ..core.extraction.document_processor import DocumentProcessor


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
    
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python -m src.cli <document_file>")
        print("\nSupported formats: PDF, PNG, JPG, JPEG")
        print("Example: python -m src.cli invoice.pdf")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        # Initialize processor
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        processor = DocumentProcessor(aws_region=aws_region)
        
        # Process document
        results = processor.process_document(file_path)
        
        # Print summary
        processor.print_summary(results)
        
        print(f"\n✅ Processing complete! Check the 'output' directory for results.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()