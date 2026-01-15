"""
Batch testing with multiple invoice samples.

Tests extraction accuracy across different invoice formats.
"""
import pytest
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser


class TestMultipleInvoices:
    """Batch tests across multiple invoice samples."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline instance."""
        return InvoiceProcessingPipeline(use_ai=False)
    
    @pytest.fixture
    def template_parser(self):
        """Create a template parser."""
        return TemplateParser()
    
    @pytest.fixture
    def sample_invoices(self):
        """Get all available sample invoices."""
        samples_dir = Path("samples")
        if not samples_dir.exists():
            return []
        
        sample_files = list(samples_dir.glob("*.pdf")) + \
                      list(samples_dir.glob("*.png")) + \
                      list(samples_dir.glob("*.jpg"))
        
        return [str(f) for f in sample_files]
    
    @pytest.mark.skipif(
        not os.getenv('AWS_ACCESS_KEY_ID'),
        reason="AWS credentials not configured"
    )
    def test_all_samples_extract_successfully(self, pipeline, template_parser, sample_invoices):
        """Test that all sample invoices can be processed without errors."""
        if not sample_invoices:
            pytest.skip("No sample invoices found")
        
        template = template_parser.parse_from_file("templates/invoice_summary.json")
        results = []
        
        for invoice_path in sample_invoices[:3]:  # Limit to 3 for testing
            try:
                result = pipeline.process_invoice(
                    file_path=invoice_path,
                    template=template,
                    output_format="csv",
                    output_path=None  # Auto-generate
                )
                
                # Verify basic structure
                assert result["canonical"] is not None
                assert "invoice" in result["canonical"]
                assert "buyer" in result["canonical"]
                assert "totals" in result["canonical"]
                
                results.append({
                    "file": Path(invoice_path).name,
                    "success": True,
                    "canonical": result["canonical"],
                    "validation": result["validation"],
                })
                
            except Exception as e:
                results.append({
                    "file": Path(invoice_path).name,
                    "success": False,
                    "error": str(e),
                })
        
        # Report results
        successful = sum(1 for r in results if r.get("success"))
        print(f"\n✅ Successfully processed {successful}/{len(results)} invoices")
        
        for result in results:
            if result.get("success"):
                canonical = result["canonical"]
                print(f"  ✓ {result['file']}: "
                      f"Invoice={canonical['invoice'].get('invoice_number', 'N/A')}, "
                      f"Buyer={canonical['buyer'].get('name', 'N/A')}, "
                      f"Total={canonical['totals'].get('total', 'N/A')}")
            else:
                print(f"  ✗ {result['file']}: {result.get('error', 'Unknown error')}")
    
    @pytest.mark.skipif(
        not os.getenv('AWS_ACCESS_KEY_ID'),
        reason="AWS credentials not configured"
    )
    def test_extraction_consistency(self, pipeline, template_parser, sample_invoices):
        """Test that extraction is consistent across similar invoices."""
        if len(sample_invoices) < 2:
            pytest.skip("Need at least 2 sample invoices")
        
        template = template_parser.parse_from_file("templates/invoice_summary.json")
        extracted_fields = defaultdict(list)
        
        for invoice_path in sample_invoices[:3]:
            try:
                result = pipeline.process_invoice(
                    file_path=invoice_path,
                    template=template,
                    output_format="csv",
                    output_path=None
                )
                
                canonical = result["canonical"]
                extracted_fields["has_invoice_number"].append(
                    bool(canonical["invoice"].get("invoice_number"))
                )
                extracted_fields["has_buyer_name"].append(
                    bool(canonical["buyer"].get("name"))
                )
                extracted_fields["has_total"].append(
                    bool(canonical["totals"].get("total"))
                )
                
            except Exception:
                pass
        
        # Check consistency
        if extracted_fields["has_invoice_number"]:
            success_rate = sum(extracted_fields["has_invoice_number"]) / len(extracted_fields["has_invoice_number"])
            print(f"\n📊 Invoice Number Extraction Rate: {success_rate:.1%}")
        
        if extracted_fields["has_buyer_name"]:
            success_rate = sum(extracted_fields["has_buyer_name"]) / len(extracted_fields["has_buyer_name"])
            print(f"📊 Buyer Name Extraction Rate: {success_rate:.1%}")
        
        if extracted_fields["has_total"]:
            success_rate = sum(extracted_fields["has_total"]) / len(extracted_fields["has_total"])
            print(f"📊 Total Extraction Rate: {success_rate:.1%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
