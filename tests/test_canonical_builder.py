"""
Unit tests for CanonicalBuilder - the core extraction logic.

Tests individual extraction methods and edge cases.
"""
import pytest
import json
from pathlib import Path
from src.core.normalize.canonical_builder import CanonicalBuilder


class TestCanonicalBuilder:
    """Test suite for CanonicalBuilder."""
    
    @pytest.fixture
    def builder(self):
        """Create a CanonicalBuilder instance."""
        return CanonicalBuilder()
    
    @pytest.fixture
    def sample_textract_results(self):
        """Sample Textract results for testing."""
        return {
            "key_value_pairs": [
                {"key": "Invoice Number", "value": "INV-001"},
                {"key": "Invoice Date", "value": "01-01-2024"},
                {"key": "To,", "value": "ABC Company Ltd."},
                {"key": "State GST No", "value": "29ABCDE1234F1Z5"},
                {"key": "Total", "value": "1000.00"},
                {"key": "Commission", "value": "800.00"},
                {"key": "ADD CGST @9%", "value": "72.00"},
                {"key": "ADD SGST @9%", "value": "72.00"},
            ],
            "tables": [],
            "text_blocks": [
                {"text": "To,", "block_type": "LINE"},
                {"text": "ABC Company Ltd.", "block_type": "LINE"},
                {"text": "State GST No", "block_type": "LINE"},
                {"text": "29ABCDE1234F1Z5", "block_type": "LINE"},
            ]
        }
    
    def test_extract_invoice_header(self, builder, sample_textract_results):
        """Test invoice header extraction."""
        header = builder._extract_invoice_header(sample_textract_results)
        
        assert header["invoice_number"] == "INV-001"
        assert header["invoice_date"] == "01-01-2024"
    
    def test_extract_buyer_info_from_to_field(self, builder, sample_textract_results):
        """Test buyer name extraction from 'To,' field."""
        buyer = builder._extract_buyer_info(sample_textract_results)
        
        assert buyer["name"] == "ABC Company Ltd."
        assert buyer["tax_id"] == "29ABCDE1234F1Z5"
    
    def test_extract_buyer_info_skips_bank_ref(self, builder):
        """Test that buyer extraction skips 'Bank Ref No.' fields."""
        results = {
            "key_value_pairs": [
                {"key": "Bank Ref No.", "value": "REF123"},
                {"key": "To,", "value": "HDFC Bank Ltd."},
            ],
            "text_blocks": [
                {"text": "To,", "block_type": "LINE"},
                {"text": "HDFC Bank Ltd.", "block_type": "LINE"},
            ]
        }
        
        buyer = builder._extract_buyer_info(results)
        assert buyer["name"] == "HDFC Bank Ltd."
        assert "Bank Ref No." not in buyer["name"]
    
    def test_extract_totals_commission_priority(self, builder):
        """Test that Commission is prioritized over Total for taxable value."""
        results = {
            "key_value_pairs": [
                {"key": "Commission", "value": "800.00"},
                {"key": "Total", "value": "1000.00"},
            ]
        }
        
        totals = builder._extract_totals(results, [])
        
        assert totals["taxable_value"] == 800.00
        assert totals["total"] == 1000.00
    
    def test_extract_cgst_sgst_from_combined_fields(self, builder):
        """Test CGST/SGST extraction from combined fields like 'ADD CGST @9%'."""
        results = {
            "key_value_pairs": [
                {"key": "ADD CGST @9%", "value": "997119 72.00"},  # HSN code first, amount second
                {"key": "ADD SGST @9%", "value": "997119 72.00"},
            ]
        }
        
        totals = builder._extract_totals(results, [])
        
        assert totals["cgst"]["rate"] == 9.0
        assert totals["cgst"]["amount"] == 72.00  # Should extract decimal value
        assert totals["sgst"]["rate"] == 9.0
        assert totals["sgst"]["amount"] == 72.00  # Should extract decimal value
    
    def test_extract_cgst_sgst_prefers_decimal(self, builder):
        """Test that CGST/SGST extraction prefers decimal values over HSN codes."""
        results = {
            "key_value_pairs": [
                {"key": "ADD CGST @9%", "value": "997119 0.00"},
                {"key": "ADD SGST @9%", "value": "22800.99 997119"},
            ]
        }
        
        totals = builder._extract_totals(results, [])
        
        # Should extract decimal value (0.00) not HSN code (997119)
        assert totals["cgst"]["amount"] == 0.0
        # Should extract decimal value (22800.99) not HSN code (997119)
        assert totals["sgst"]["amount"] == 22800.99
    
    def test_extract_total_when_taxable_exists(self, builder):
        """Test that Total is extracted when taxable_value already exists."""
        results = {
            "key_value_pairs": [
                {"key": "Commission", "value": "800.00"},
                {"key": "Total", "value": "1000.00"},
            ]
        }
        
        totals = builder._extract_totals(results, [])
        
        assert totals["taxable_value"] == 800.00
        assert totals["total"] == 1000.00
    
    def test_normalize_amount_handles_commas(self, builder):
        """Test that amount normalization handles comma-separated numbers."""
        assert builder._normalize_amount("1,000.00") == 1000.00
        assert builder._normalize_amount("10,000.50") == 10000.50
        assert builder._normalize_amount("1,23,456.78") == 123456.78
    
    def test_normalize_percentage_extracts_rate(self, builder):
        """Test percentage normalization extracts numeric rate."""
        assert builder._normalize_percentage("9%") == 9.0
        assert builder._normalize_percentage("CGST 9%") == 9.0
        assert builder._normalize_percentage("ADD CGST @9%") == 9.0
        assert builder._normalize_percentage("18.5%") == 18.5
    
    def test_looks_like_amount(self, builder):
        """Test amount detection logic."""
        assert builder._looks_like_amount("1000.00") == True
        assert builder._looks_like_amount("1,000.00") == True
        assert builder._looks_like_amount("ABC Company") == False
        assert builder._looks_like_amount("29ABCDE1234F1Z5") == False
    
    def test_build_complete_canonical(self, builder, sample_textract_results):
        """Test building a complete canonical model."""
        canonical = builder.build(sample_textract_results)
        
        assert canonical["invoice"]["invoice_number"] == "INV-001"
        assert canonical["buyer"]["name"] == "ABC Company Ltd."
        assert canonical["totals"]["taxable_value"] == 800.00
        assert canonical["totals"]["total"] == 1000.00
        assert canonical["totals"]["cgst"]["amount"] == 72.00
        assert canonical["totals"]["sgst"]["amount"] == 72.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
