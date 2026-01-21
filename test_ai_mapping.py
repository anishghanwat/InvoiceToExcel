"""
Test script for AI-powered header mapping.
"""
import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.core.templates.template_parser import TemplateParser
from src.core.pipeline import InvoiceProcessingPipeline

def test_ai_mapping():
    """Test AI-powered header mapping with actual invoice."""
    print("🧪 Testing AI-Powered Header Mapping")
    print("=" * 60)
    
    # Step 1: Process a sample invoice
    print("\n📄 Step 1: Processing sample invoice...")
    pipeline = InvoiceProcessingPipeline(use_ai=True)
    
    sample_file = "gstpendinginvoices/MMFPL-45-2025-26.pdf"
    if not os.path.exists(sample_file):
        print(f"❌ Sample file not found: {sample_file}")
        return
    
    result = pipeline.process_invoice(sample_file, output_format="json")
    canonical_sample = result.get('canonical', {})
    
    print("✅ Sample processed")
    print(f"   Invoice: {canonical_sample.get('invoice', {}).get('invoice_number', 'N/A')}")
    print(f"   Buyer: {canonical_sample.get('buyer', {}).get('name', 'N/A')}")
    
    # Step 2: Test CSV template parsing with AI
    print("\n📋 Step 2: Testing CSV template with AI mapping...")
    template_path = "ExampleTempates/final_output.csv"
    
    if not os.path.exists(template_path):
        print(f"❌ Template file not found: {template_path}")
        return
    
    parser = TemplateParser()
    
    # Test with AI mapping
    print("\n🤖 Testing with AI mapping...")
    try:
        template_ai = parser.parse_from_file(
            template_path,
            canonical_sample=canonical_sample,
            use_ai_mapping=True
        )
        print("✅ AI mapping successful!")
        print(f"\n📊 Mapped Columns:")
        for col in template_ai.get('columns', []):
            print(f"   {col['header']:20} → {col['path']}")
    except Exception as e:
        print(f"❌ AI mapping failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test without AI (keyword matching)
    print("\n🔤 Testing with keyword matching (fallback)...")
    try:
        template_keyword = parser.parse_from_file(
            template_path,
            use_ai_mapping=False
        )
        print("✅ Keyword matching successful!")
        print(f"\n📊 Mapped Columns:")
        for col in template_keyword.get('columns', []):
            print(f"   {col['header']:20} → {col['path']}")
    except Exception as e:
        print(f"❌ Keyword matching failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")

if __name__ == '__main__':
    test_ai_mapping()
