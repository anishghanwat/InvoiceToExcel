"""
Test script to demonstrate using default templates.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser
from src.core.templates.exporter import TemplateExporter

# Load environment variables
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def main():
    """Test default templates."""
    print("=" * 70)
    print("  Testing Default Templates")
    print("=" * 70)
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Error: AWS credentials not found!")
        return
    
    # Find a sample invoice
    sample_dir = Path("samples")
    sample_files = list(sample_dir.glob("*.pdf")) + list(sample_dir.glob("*.png")) + list(sample_dir.glob("*.jpg"))
    
    if not sample_files:
        print(f"❌ Error: No sample invoices found")
        return
    
    sample_file = sample_files[0]
    print(f"\n📄 Using sample: {sample_file.name}\n")
    
    try:
        # Initialize
        pipeline = InvoiceProcessingPipeline(use_ai=os.getenv('GEMINI_API_KEY') is not None)
        template_parser = TemplateParser()
        exporter = TemplateExporter()
        
        # Process invoice once
        print("🔄 Processing invoice...")
        result = pipeline.process_invoice(
            file_path=str(sample_file),
            output_format="json"
        )
        canonical = result["canonical"]
        print("✅ Invoice processed\n")
        
        # List available templates
        print("📋 Available Templates:")
        templates = template_parser.list_default_templates()
        for i, template_name in enumerate(templates, 1):
            print(f"   {i}. {template_name}")
        print()
        
        # Test each template
        base_name = sample_file.stem
        
        for template_name in templates:
            try:
                print(f"📊 Exporting with '{template_name}' template...")
                template = template_parser.load_default_template(template_name)
                
                output_path = f"output/{base_name}_{template_name}.csv"
                exporter.export_to_csv(canonical, template, output_path)
                print(f"   ✅ Created: {output_path}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        print("\n" + "=" * 70)
        print("✅ Template testing complete!")
        print(f"\n📁 Check the 'output' directory for exported files:")
        for template_name in templates:
            print(f"   - {base_name}_{template_name}.csv")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
