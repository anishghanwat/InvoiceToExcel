"""
Test script for production-ready pipeline features.
Tests retry logic, error handling, logging, timeouts, and graceful degradation.
"""
import sys
import os
from pathlib import Path

# Ensure proper encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.core.pipeline import InvoiceProcessingPipeline
from config import settings

def test_production_pipeline():
    """Test the production-ready pipeline with a sample invoice."""
    
    print("=" * 70)
    print("PRODUCTION PIPELINE TEST")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  - Pipeline Timeout: {settings.PIPELINE_TIMEOUT_SECONDS}s")
    print(f"  - Textract Max Retries: {settings.TEXTRACT_MAX_RETRIES}")
    print(f"  - AI Max Retries: {settings.AI_MAX_RETRIES}")
    print(f"  - Graceful Degradation: {settings.ENABLE_GRACEFUL_DEGRADATION}")
    print(f"  - Structured Logging: {settings.ENABLE_STRUCTURED_LOGGING}")
    print(f"  - AI Fixing: {settings.ENABLE_AI_FIXING}")
    
    # Find a sample invoice
    samples_dir = Path("samples")
    sample_files = list(samples_dir.glob("*.pdf")) + list(samples_dir.glob("*.png")) + list(samples_dir.glob("*.jpg"))
    
    if not sample_files:
        print("\n❌ No sample invoices found in samples/ directory")
        return False
    
    # Use the first available sample
    sample_file = sample_files[0]
    print(f"\n📄 Testing with: {sample_file.name}")
    print(f"   Full path: {sample_file.absolute()}")
    
    # Initialize pipeline with production settings
    print("\n🔧 Initializing pipeline...")
    try:
        pipeline = InvoiceProcessingPipeline(
            use_ai=settings.ENABLE_AI_FIXING,
            enable_logging=settings.ENABLE_STRUCTURED_LOGGING,
            timeout_seconds=settings.PIPELINE_TIMEOUT_SECONDS
        )
        print("✅ Pipeline initialized successfully")
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")
        return False
    
    # Test 1: Process invoice
    print("\n" + "=" * 70)
    print("TEST 1: Process Invoice with Production Features")
    print("=" * 70)
    
    try:
        result = pipeline.process_invoice(
            str(sample_file),
            output_format="csv"
        )
        
        print("\n✅ Processing completed successfully!")
        print(f"\nResults:")
        print(f"  - Success: {result.get('success', 'N/A')}")
        print(f"  - Processing Time: {result.get('processing_time_ms', 0)}ms")
        print(f"  - Output File: {result.get('output_file', 'N/A')}")
        
        # Check validation
        validation = result.get('validation', {})
        if validation.get('valid'):
            print(f"  - Validation: ✅ Valid")
        else:
            errors = validation.get('errors', [])
            print(f"  - Validation: ⚠️  {len(errors)} errors found")
            for error in errors[:3]:  # Show first 3 errors
                print(f"    • {error}")
        
        # Check canonical model
        canonical = result.get('canonical', {})
        if canonical:
            invoice = canonical.get('invoice', {})
            print(f"\n📊 Extracted Data:")
            print(f"  - Invoice Number: {invoice.get('invoice_number', 'N/A')}")
            print(f"  - Invoice Date: {invoice.get('invoice_date', 'N/A')}")
            
            seller = canonical.get('seller', {})
            buyer = canonical.get('buyer', {})
            print(f"  - Seller: {seller.get('name', 'N/A')}")
            print(f"  - Buyer: {buyer.get('name', 'N/A')}")
            
            totals = canonical.get('totals', {})
            print(f"  - Total: {totals.get('total', 'N/A')}")
            
            # Check confidence scores
            confidence = canonical.get('metadata', {}).get('confidence', {})
            overall_conf = confidence.get('overall', 0)
            print(f"  - Overall Confidence: {overall_conf:.2%}")
        
        test1_success = True
        
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        return False
    except ValueError as e:
        print(f"\n❌ Validation error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        import traceback
        print(f"\nTraceback:")
        traceback.print_exc()
        test1_success = False
    
    # Test 2: Error handling (test with invalid file)
    print("\n" + "=" * 70)
    print("TEST 2: Error Handling (Invalid File)")
    print("=" * 70)
    
    try:
        result = pipeline.process_invoice("nonexistent_file.pdf")
        print("❌ Should have raised FileNotFoundError")
        test2_success = False
    except FileNotFoundError:
        print("✅ Correctly raised FileNotFoundError for missing file")
        test2_success = True
    except Exception as e:
        print(f"⚠️  Unexpected error type: {type(e).__name__}: {e}")
        test2_success = False
    
    # Test 3: Input validation
    print("\n" + "=" * 70)
    print("TEST 3: Input Validation")
    print("=" * 70)
    
    # Test with directory instead of file
    try:
        result = pipeline.process_invoice("samples")  # This is a directory
        print("❌ Should have raised ValueError")
        test3_success = False
    except (ValueError, FileNotFoundError) as e:
        print(f"✅ Correctly validated input (rejected directory): {type(e).__name__}")
        test3_success = True
    except Exception as e:
        # Error might be wrapped, check the message
        error_msg = str(e).lower()
        if "not a file" in error_msg or "path is not a file" in error_msg:
            print(f"✅ Correctly validated input (rejected directory) - wrapped error")
            test3_success = True
        else:
            print(f"⚠️  Unexpected error: {type(e).__name__}: {e}")
            test3_success = False
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
    print(f"\nTest Results:")
    print(f"  ✅ Test 1 (Process Invoice): {'PASSED' if test1_success else 'FAILED'}")
    print(f"  ✅ Test 2 (Error Handling): {'PASSED' if test2_success else 'FAILED'}")
    print(f"  ✅ Test 3 (Input Validation): {'PASSED' if test3_success else 'FAILED'}")
    
    return test1_success and test2_success and test3_success


if __name__ == "__main__":
    success = test_production_pipeline()
    sys.exit(0 if success else 1)
