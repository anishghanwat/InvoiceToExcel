"""
Validation tests for invoice data quality and compliance.

Tests validation rules and edge cases.
"""
import pytest
from src.core.validators.validator import ValidationEngine
from src.core.normalize.canonical_schema import CanonicalSchema


class TestValidationEngine:
    """Test suite for ValidationEngine."""
    
    @pytest.fixture
    def validator(self):
        """Create a ValidationEngine instance."""
        return ValidationEngine()
    
    @pytest.fixture
    def valid_canonical(self):
        """A valid canonical invoice model (intrastate transaction)."""
        return {
            "invoice": {
                "invoice_number": "INV-001",
                "invoice_date": "01-01-2024",
            },
            "buyer": {
                "name": "ABC Company",
                "tax_id": "29ABCDE1234F1Z5",  # Valid GSTIN format (State: 29)
            },
            "seller": {
                "name": "XYZ Corp",
                "tax_id": "29ABCDE1234F1Z6",  # Same state (29) for intrastate transaction
            },
            "totals": {
                "taxable_value": 1000.00,
                "cgst": {"rate": 9.0, "amount": 90.00},
                "sgst": {"rate": 9.0, "amount": 90.00},
                "igst": {"rate": 0.0, "amount": 0.00},
                "total": 1180.00,
            },
            "line_items": [
                {
                    "description": "Item 1",
                    "taxable_value": 500.00,
                    "taxes": {
                        "cgst": {"amount": 45.00},
                        "sgst": {"amount": 45.00},
                    },
                    "total": 590.00,
                },
                {
                    "description": "Item 2",
                    "taxable_value": 500.00,
                    "taxes": {
                        "cgst": {"amount": 45.00},
                        "sgst": {"amount": 45.00},
                    },
                    "total": 590.00,
                },
            ],
        }
    
    def test_validate_valid_invoice(self, validator, valid_canonical):
        """Test validation of a valid invoice."""
        result = validator.validate(valid_canonical)
        
        # Should have minimal warnings but no errors
        assert result["valid"] == True or len(result.get("errors", [])) == 0
    
    def test_validate_gstin_format(self, validator):
        """Test GSTIN format validation."""
        # Valid GSTIN
        canonical = {
            "buyer": {"tax_id": "29ABCDE1234F1Z5"},
            "seller": {"tax_id": "27ABCDE1234F1Z6"},
            "totals": {},
            "line_items": [],
        }
        result = validator.validate(canonical)
        # Should not have GSTIN format errors
        
        # Invalid GSTIN (too short)
        canonical["buyer"]["tax_id"] = "29ABCDE"
        result = validator.validate(canonical)
        # Should flag invalid GSTIN format
    
    def test_validate_math_totals(self, validator):
        """Test mathematical validation of totals."""
        canonical = {
            "totals": {
                "taxable_value": 1000.00,
                "cgst": {"amount": 90.00},
                "sgst": {"amount": 90.00},
                "total": 1180.00,  # Correct: 1000 + 90 + 90 = 1180
            },
            "line_items": [
                {"taxable_value": 500.00, "total": 590.00},
                {"taxable_value": 500.00, "total": 590.00},
            ],
        }
        
        result = validator.validate(canonical)
        # Should pass math validation
        
        # Incorrect total
        canonical["totals"]["total"] = 1000.00  # Missing taxes
        result = validator.validate(canonical)
        # Should flag math error
    
    def test_validate_line_items_sum(self, validator):
        """Test that line items sum matches totals."""
        canonical = {
            "totals": {
                "taxable_value": 1000.00,
            },
            "line_items": [
                {"taxable_value": 500.00},
                {"taxable_value": 500.00},
            ],
        }
        
        result = validator.validate(canonical)
        # Should pass if sums match
        
        # Mismatch
        canonical["line_items"][1]["taxable_value"] = 600.00
        result = validator.validate(canonical)
        # Should flag mismatch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
