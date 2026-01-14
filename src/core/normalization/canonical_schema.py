"""
Canonical Invoice Schema - Final Production Version
This is the backbone of the product.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime


class CanonicalSchema:
    """Canonical invoice schema following exact production specification."""
    
    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """Create empty canonical invoice structure."""
        return {
            "invoice_id": None,
            "invoice_date": None,
            "due_date": None,
            
            "vendor": {
                "name": None,
                "address": None,
                "tax_id": None
            },
            
            "customer": {
                "name": None,
                "address": None
            },
            
            "amounts": {
                "subtotal": None,
                "tax": None,
                "discount": None,
                "total": None,
                "currency": "USD"
            },
            
            "line_items": [],
            
            "confidence": {
                "overall": 0.0,
                "fields": {}
            },
            
            "metadata": {
                "source": "textract",
                "ai_version": None,
                "processing_time_ms": 0
            }
        }
    
    @staticmethod
    def from_deterministic_mapping(canonical: Dict[str, Any]) -> Dict[str, Any]:
        """Convert deterministic mapping output to canonical schema."""
        schema = CanonicalSchema.create_empty()
        
        # Map fields
        schema["invoice_id"] = canonical.get("invoice_number")
        schema["invoice_date"] = canonical.get("invoice_date")
        schema["due_date"] = None  # Not extracted in deterministic layer
        
        # Vendor
        vendor_name = canonical.get("vendor")
        if vendor_name:
            schema["vendor"]["name"] = vendor_name
        schema["vendor"]["tax_id"] = canonical.get("tax_id")
        
        # Customer
        customer_name = canonical.get("customer")
        if customer_name:
            schema["customer"]["name"] = customer_name
        
        # Amounts
        schema["amounts"]["subtotal"] = canonical.get("subtotal")
        schema["amounts"]["tax"] = canonical.get("tax_amount")
        schema["amounts"]["total"] = canonical.get("total_amount")
        schema["amounts"]["currency"] = canonical.get("currency", "USD")
        
        # Line items
        for item in canonical.get("line_items", []):
            schema["line_items"].append({
                "description": item.get("description", ""),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "total": item.get("amount")
            })
        
        return schema
    
    @staticmethod
    def to_legacy_format(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert canonical schema back to legacy format for CSV generation."""
        return {
            "invoice_number": schema.get("invoice_id"),
            "invoice_date": schema.get("invoice_date"),
            "vendor": schema.get("vendor", {}).get("name"),
            "customer": schema.get("customer", {}).get("name"),
            "order_number": None,  # Not in canonical schema
            "tax_id": schema.get("vendor", {}).get("tax_id"),
            "currency": schema.get("amounts", {}).get("currency"),
            "subtotal": schema.get("amounts", {}).get("subtotal"),
            "tax_amount": schema.get("amounts", {}).get("tax"),
            "total_amount": schema.get("amounts", {}).get("total"),
            "line_items": [
                {
                    "description": item.get("description"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "amount": item.get("total"),
                    "tax_rate": None,
                    "tax_amount": None
                }
                for item in schema.get("line_items", [])
            ]
        }
