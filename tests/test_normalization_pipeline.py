"""
Test the 4-layer normalization pipeline.
"""
import sys
import json
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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.normalization.normalization_pipeline import NormalizationPipeline

def test_normalization():
    """Test normalization pipeline on sample invoice."""
    print("=" * 70)
    print("🧪 Testing 4-Layer Normalization Pipeline")
    print("=" * 70)
    
    # Load sample results
    project_root = Path(__file__).parent.parent
    results_file = project_root / "output" / "amazon_invoice_results.json"
    if not results_file.exists():
        print(f"❌ Results file not found: {results_file}")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Get document text for context
    document_text = ' '.join([
        block.get('text', '') for block in results.get('text_blocks', [])[:50]
    ])
    
    # Initialize pipeline
    print("\n📦 Initializing pipeline...")
    pipeline = NormalizationPipeline(use_ai=True)
    
    # Run normalization
    print("\n🔄 Running normalization pipeline...")
    normalized = pipeline.normalize(results, document_text)
    
    # Display results
    print("\n" + "=" * 70)
    print("📊 NORMALIZATION RESULTS")
    print("=" * 70)
    
    canonical = normalized['canonical']
    validation = normalized['validation']
    
    print("\n✅ CANONICAL DATA:")
    print(f"   Invoice Number: {canonical.get('invoice_number', 'N/A')}")
    print(f"   Invoice Date: {canonical.get('invoice_date', 'N/A')}")
    print(f"   Vendor: {canonical.get('vendor', 'N/A')[:60]}...")
    print(f"   Customer: {canonical.get('customer', 'N/A')[:60]}...")
    print(f"   Order Number: {canonical.get('order_number', 'N/A')}")
    print(f"   Tax ID: {canonical.get('tax_id', 'N/A')}")
    print(f"   Currency: {canonical.get('currency', 'N/A')}")
    print(f"   Subtotal: {canonical.get('subtotal', 'N/A')}")
    print(f"   Tax Amount: {canonical.get('tax_amount', 'N/A')}")
    print(f"   Tax Rate: {canonical.get('tax_rate', 'N/A')}")
    print(f"   Total Amount: {canonical.get('total_amount', 'N/A')}")
    print(f"   Line Items: {len(canonical.get('line_items', []))}")
    
    print("\n✅ VALIDATION RESULTS:")
    print(f"   Is Valid: {validation.get('is_valid', False)}")
    print(f"   Overall Confidence: {validation.get('confidence', 0.0):.2%}")
    print(f"   Needs Repair: {validation.get('needs_repair', False)}")
    
    math_checks = validation.get('math_checks', {})
    if math_checks:
        print(f"\n   Math Checks:")
        print(f"      Subtotal + Tax = Total: {math_checks.get('subtotal_tax_total_match', False)}")
        print(f"      Calculated Total: {math_checks.get('calculated_total', 0)}")
        print(f"      Reported Total: {math_checks.get('reported_total', 0)}")
        print(f"      Difference: {math_checks.get('difference', 0)}")
    
    if validation.get('errors'):
        print(f"\n   ❌ Errors: {validation.get('errors')}")
    
    if validation.get('warnings'):
        print(f"\n   ⚠️  Warnings: {validation.get('warnings')}")
    
    print("\n" + "=" * 70)
    print("✅ Normalization complete!")
    print("=" * 70)

if __name__ == '__main__':
    test_normalization()
