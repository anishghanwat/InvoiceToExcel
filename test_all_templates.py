"""
Comprehensive test for all templates.
Tests each template individually and verifies output.
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
import csv

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


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def verify_csv_file(file_path: str, template_name: str) -> dict:
    """
    Verify a CSV file was created correctly.
    
    Returns:
        Dict with verification results
    """
    result = {
        "exists": False,
        "has_header": False,
        "has_data": False,
        "row_count": 0,
        "column_count": 0,
        "errors": []
    }
    
    if not os.path.exists(file_path):
        result["errors"].append(f"File does not exist: {file_path}")
        return result
    
    result["exists"] = True
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            if len(rows) == 0:
                result["errors"].append("File is empty")
                return result
            
            # Check header
            if len(rows) > 0:
                result["has_header"] = True
                result["column_count"] = len(rows[0])
            
            # Check data rows
            if len(rows) > 1:
                result["has_data"] = True
                result["row_count"] = len(rows) - 1  # Exclude header
            
            # Basic validation
            if result["column_count"] == 0:
                result["errors"].append("No columns found")
            
            if result["row_count"] == 0:
                result["errors"].append("No data rows found")
                
    except Exception as e:
        result["errors"].append(f"Error reading file: {str(e)}")
    
    return result


def main():
    """Test all templates comprehensively."""
    print_section("Comprehensive Template Testing")
    
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
        print("🔄 Processing invoice (this may take a moment)...")
        result = pipeline.process_invoice(
            file_path=str(sample_file),
            output_format="json"
        )
        canonical = result["canonical"]
        print("✅ Invoice processed successfully\n")
        
        # Get all templates
        template_names = template_parser.list_default_templates()
        print(f"📋 Testing {len(template_names)} templates:\n")
        
        # Test results
        test_results = {}
        base_name = sample_file.stem.replace(" ", "_")
        
        for template_name in template_names:
            print(f"🧪 Testing '{template_name}' template...")
            
            try:
                # Load template
                template = template_parser.load_default_template(template_name)
                print(f"   ✓ Template loaded: {template.get('name', template_name)}")
                
                # Generate unique output path
                output_path = f"output/{base_name}_test_{template_name}.csv"
                
                # Export
                exporter.export_to_csv(canonical, template, output_path)
                print(f"   ✓ CSV exported: {output_path}")
                
                # Verify file
                verification = verify_csv_file(output_path, template_name)
                
                if verification["exists"] and verification["has_header"] and verification["has_data"]:
                    print(f"   ✅ Verified: {verification['row_count']} rows, {verification['column_count']} columns")
                    test_results[template_name] = {
                        "status": "PASS",
                        "file": output_path,
                        "rows": verification["row_count"],
                        "columns": verification["column_count"]
                    }
                else:
                    errors = ", ".join(verification["errors"])
                    print(f"   ⚠️  Verification issues: {errors}")
                    test_results[template_name] = {
                        "status": "WARNING",
                        "file": output_path,
                        "errors": verification["errors"]
                    }
                
            except FileNotFoundError as e:
                print(f"   ❌ Template file not found: {e}")
                test_results[template_name] = {"status": "FAIL", "error": str(e)}
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                test_results[template_name] = {"status": "FAIL", "error": str(e)}
            
            print()
        
        # Summary
        print_section("Test Summary")
        
        passed = sum(1 for r in test_results.values() if r.get("status") == "PASS")
        warnings = sum(1 for r in test_results.values() if r.get("status") == "WARNING")
        failed = sum(1 for r in test_results.values() if r.get("status") == "FAIL")
        
        print(f"✅ Passed: {passed}/{len(template_names)}")
        if warnings > 0:
            print(f"⚠️  Warnings: {warnings}/{len(template_names)}")
        if failed > 0:
            print(f"❌ Failed: {failed}/{len(template_names)}")
        
        print("\n📊 Detailed Results:")
        for template_name, result in test_results.items():
            status_icon = "✅" if result.get("status") == "PASS" else "⚠️" if result.get("status") == "WARNING" else "❌"
            print(f"   {status_icon} {template_name}: {result.get('status', 'UNKNOWN')}")
            if result.get("status") == "PASS":
                print(f"      Rows: {result.get('rows', 0)}, Columns: {result.get('columns', 0)}")
            elif result.get("errors"):
                for error in result.get("errors", []):
                    print(f"      - {error}")
            elif result.get("error"):
                print(f"      - {result.get('error')}")
        
        print_section("Test Complete")
        print(f"📁 All test files saved in 'output/' directory with prefix: {base_name}_test_")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
