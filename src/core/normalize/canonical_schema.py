"""
Rich Canonical Invoice Schema - Single Source of Truth
This is richer than any output template. It captures ALL invoice data.

Key Principle: Canonical model is stable, templates are unlimited.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime


class CanonicalSchema:
    """
    Rich canonical invoice schema that captures all possible invoice data.
    This must be richer than any output template.
    """
    
    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """
        Create empty canonical invoice structure.
        
        This schema is designed to be richer than any output format.
        You can collapse rich → simple, but cannot expand simple → rich.
        """
        return {
            # Invoice identification
            "invoice": {
                "invoice_number": None,
                "invoice_date": None,
                "due_date": None,
                "order_number": None,
                "po_number": None,
                "payment_terms": None,
                "place_of_supply": None,
            },
            
            # Seller/Vendor information (rich structure)
            "seller": {
                "name": None,
                "legal_name": None,
                "address": {
                    "line1": None,
                    "line2": None,
                    "city": None,
                    "state": None,
                    "postal_code": None,
                    "country": None,
                },
                "tax_id": None,  # GSTIN, VAT, etc.
                "pan": None,
                "contact": {
                    "phone": None,
                    "email": None,
                    "website": None,
                }
            },
            
            # Buyer/Customer information (rich structure)
            "buyer": {
                "name": None,
                "legal_name": None,
                "address": {
                    "line1": None,
                    "line2": None,
                    "city": None,
                    "state": None,
                    "postal_code": None,
                    "country": None,
                },
                "tax_id": None,  # GSTIN, VAT, etc.
                "pan": None,
                "contact": {
                    "phone": None,
                    "email": None,
                }
            },
            
            # Line items (detailed structure)
            "line_items": [
                # Each item has:
                # {
                #   "line_number": 1,
                #   "description": "...",
                #   "hsn": None,  # HSN/SAC code
                #   "quantity": 1.0,
                #   "unit": None,  # "pcs", "kg", etc.
                #   "unit_price": 100.0,
                #   "discount": 0.0,
                #   "taxable_value": 100.0,
                #   "taxes": {
                #     "cgst": {"rate": 9.0, "amount": 9.0},
                #     "sgst": {"rate": 9.0, "amount": 9.0},
                #     "igst": {"rate": 0.0, "amount": 0.0},
                #     "cess": {"rate": 0.0, "amount": 0.0},
                #   },
                #   "total": 118.0
                # }
            ],
            
            # Totals (rich breakdown)
            "totals": {
                "taxable_value": None,  # Sum of all line item taxable values
                "discount": None,
                "cgst": {
                    "rate": None,  # Common rate if uniform
                    "amount": None
                },
                "sgst": {
                    "rate": None,
                    "amount": None
                },
                "igst": {
                    "rate": None,
                    "amount": None
                },
                "cess": {
                    "rate": None,
                    "amount": None
                },
                "round_off": None,
                "total": None,
                "currency": "INR"  # Default, can be USD, EUR, etc.
            },
            
            # Additional information
            "shipping": {
                "shipped_to": None,
                "shipping_address": None,
                "tracking_number": None,
            },
            
            # Metadata
            "metadata": {
                "source": "textract",
                "extraction_date": None,
                "ai_version": None,
                "processing_time_ms": 0,
                "ledger": None,  # Ledger account name/code
                "notes": None,  # Additional notes
                "confidence": {
                    "overall": 0.0,
                    "fields": {}
                }
            }
        }
    
    @staticmethod
    def validate_structure(canonical: Dict[str, Any]) -> bool:
        """
        Validate that a dictionary follows canonical schema structure.
        
        Args:
            canonical: Dictionary to validate
            
        Returns:
            True if structure is valid
        """
        required_keys = ["invoice", "seller", "buyer", "line_items", "totals", "metadata"]
        return all(key in canonical for key in required_keys)
    
    @staticmethod
    def get_tax_breakdown(canonical: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract tax breakdown from canonical model.
        
        Returns:
            Dict with cgst, sgst, igst amounts
        """
        totals = canonical.get("totals", {})
        return {
            "cgst": totals.get("cgst", {}).get("amount", 0.0) or 0.0,
            "sgst": totals.get("sgst", {}).get("amount", 0.0) or 0.0,
            "igst": totals.get("igst", {}).get("amount", 0.0) or 0.0,
            "cess": totals.get("cess", {}).get("amount", 0.0) or 0.0,
        }
    
    @staticmethod
    def get_total_tax(canonical: Dict[str, Any]) -> float:
        """Get total tax amount (CGST + SGST + IGST + CESS)."""
        breakdown = CanonicalSchema.get_tax_breakdown(canonical)
        return breakdown["cgst"] + breakdown["sgst"] + breakdown["igst"] + breakdown["cess"]
    
    @staticmethod
    def is_interstate(canonical: Dict[str, Any]) -> bool:
        """
        Determine if invoice is interstate (IGST) or intrastate (CGST+SGST).
        
        Returns:
            True if interstate (IGST > 0), False if intrastate
        """
        totals = canonical.get("totals", {})
        igst_amount = totals.get("igst", {}).get("amount", 0.0) or 0.0
        return igst_amount > 0
