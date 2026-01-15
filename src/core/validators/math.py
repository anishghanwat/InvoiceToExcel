"""
Math Validation - Validates invoice totals match line items.
"""
from typing import Dict, Any, List


class MathValidator:
    """Validates mathematical consistency in canonical invoice model."""
    
    def validate(self, canonical: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate mathematical consistency.
        
        Checks:
        - Invoice totals = sum(line items)
        - Taxable value = sum(line item taxable values)
        - Total tax = sum(line item taxes)
        - Total = taxable + taxes
        
        Args:
            canonical: Canonical invoice model
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        line_items = canonical.get("line_items", [])
        totals = canonical.get("totals", {})
        
        # Calculate from line items
        calculated_taxable = sum(
            item.get("taxable_value", 0.0) or 0.0
            for item in line_items
        )
        
        calculated_cgst = sum(
            item.get("taxes", {}).get("cgst", {}).get("amount", 0.0) or 0.0
            for item in line_items
        )
        
        calculated_sgst = sum(
            item.get("taxes", {}).get("sgst", {}).get("amount", 0.0) or 0.0
            for item in line_items
        )
        
        calculated_igst = sum(
            item.get("taxes", {}).get("igst", {}).get("amount", 0.0) or 0.0
            for item in line_items
        )
        
        calculated_total_tax = calculated_cgst + calculated_sgst + calculated_igst
        
        calculated_total = calculated_taxable + calculated_total_tax
        
        # Compare with totals
        declared_taxable = totals.get("taxable_value")
        if declared_taxable is not None:
            if abs(declared_taxable - calculated_taxable) > 0.01:
                errors.append(
                    f"Taxable value mismatch: declared {declared_taxable}, "
                    f"calculated from line items {calculated_taxable:.2f}"
                )
        
        declared_cgst = totals.get("cgst", {}).get("amount")
        if declared_cgst is not None and calculated_cgst > 0:
            if abs(declared_cgst - calculated_cgst) > 0.01:
                errors.append(
                    f"CGST amount mismatch: declared {declared_cgst}, "
                    f"calculated from line items {calculated_cgst:.2f}"
                )
        
        declared_sgst = totals.get("sgst", {}).get("amount")
        if declared_sgst is not None and calculated_sgst > 0:
            if abs(declared_sgst - calculated_sgst) > 0.01:
                errors.append(
                    f"SGST amount mismatch: declared {declared_sgst}, "
                    f"calculated from line items {calculated_sgst:.2f}"
                )
        
        declared_igst = totals.get("igst", {}).get("amount")
        if declared_igst is not None and calculated_igst > 0:
            if abs(declared_igst - calculated_igst) > 0.01:
                errors.append(
                    f"IGST amount mismatch: declared {declared_igst}, "
                    f"calculated from line items {calculated_igst:.2f}"
                )
        
        declared_total = totals.get("total")
        if declared_total is not None:
            if abs(declared_total - calculated_total) > 0.01:
                errors.append(
                    f"Total amount mismatch: declared {declared_total}, "
                    f"calculated from line items {calculated_total:.2f}"
                )
        
        # Check: total = taxable + taxes
        if declared_taxable is not None and declared_total is not None:
            expected_total = declared_taxable + calculated_total_tax
            if abs(declared_total - expected_total) > 0.01:
                errors.append(
                    f"Total does not equal taxable + taxes: "
                    f"total={declared_total}, taxable={declared_taxable}, "
                    f"taxes={calculated_total_tax:.2f}"
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
