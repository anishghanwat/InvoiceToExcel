"""
Integration tests for the complete invoice processing pipeline.

Tests the full flow: Textract → Canonical → Validation → Export
"""
import pytest
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.core.pipeline import InvoiceProcessingPipeline
from src.core.templates.template_parser import TemplateParser
from src.core.templates.exporter import TemplateExporter


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline instance (AI disabled for faster tests)."""
        return InvoiceProcessingPipeline(use_ai=False)
    
    @pytest.fixture
    def template_parser(self):
        """Create a template parser."""
        return TemplateParser()
    
    @pytest.fixture
    def sample_invoice_path(self):
        """Get path to a sample invoice."""
        samples_dir = Path("samples")
        if not samples_dir.exists():
            pytest.skip("Samples directory not found")
        
        # Try to find a sample invoice
        sample_files = list(samples_dir.glob("*.pdf")) + \
                      list(samples_dir.glob("*.png")) + \
                      list(samples_dir.glob("*.jpg"))
        
        if not sample_files:
            pytest.skip("No sample invoices found")
        
        return str(sample_files[0])
    
    @pytest.mark.skipif(
        not os.getenv('AWS_ACCESS_KEY_ID'),
        reason="AWS credentials not configured"
    )
    def test_full_pipeline_processing(self, pipeline, template_parser, sample_invoice_path, tmp_path):
        """Test the complete pipeline processing."""
        # Load a template
        template = template_parser.parse_from_file("templates/invoice_summary.json")
        
        # Process invoice
        output_path = str(tmp_path / "test_export.csv")
        result = pipeline.process_invoice(
            file_path=sample_invoice_path,
            template=template,
            output_format="csv",
            output_path=output_path
        )
        
        # Verify result structure
        assert "canonical" in result
        assert "validation" in result
        assert "output_file" in result
        
        # Verify canonical model structure
        canonical = result["canonical"]
        assert "invoice" in canonical
        assert "buyer" in canonical
        assert "seller" in canonical
        assert "totals" in canonical
        assert "line_items" in canonical
        
        # Verify output file exists
        assert Path(result["output_file"]).exists()
    
    @pytest.mark.skipif(
        not os.getenv('AWS_ACCESS_KEY_ID'),
        reason="AWS credentials not configured"
    )
    def test_pipeline_with_different_templates(self, pipeline, template_parser, sample_invoice_path, tmp_path):
        """Test pipeline with different templates."""
        templates_to_test = [
            "templates/invoice_summary.json",
            "templates/simple_invoice.json",
        ]
        
        for template_path in templates_to_test:
            if not Path(template_path).exists():
                continue
            
            template = template_parser.parse_from_file(template_path)
            output_path = str(tmp_path / f"test_{Path(template_path).stem}.csv")
            
            result = pipeline.process_invoice(
                file_path=sample_invoice_path,
                template=template,
                output_format="csv",
                output_path=output_path
            )
            
            assert result["canonical"] is not None
            assert Path(output_path).exists()
    
    def test_pipeline_handles_missing_file(self, pipeline):
        """Test that pipeline handles missing file gracefully."""
        with pytest.raises(Exception):
            pipeline.process_invoice(
                file_path="nonexistent_file.pdf",
                template=None,
                output_format="csv",
                output_path="output/test.csv"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
