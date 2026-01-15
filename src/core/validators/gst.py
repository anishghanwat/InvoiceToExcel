"""
GST Validation - Validates GSTIN format, state codes, tax logic.
"""
import re
from typing import Dict, Any, List, Optional


class GSTValidator:
    """Validates GST-related fields in canonical invoice model."""
    
    def validate(self, canonical: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate GST fields.
        
        Args:
            canonical: Canonical invoice model
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        # Validate seller GSTIN
        seller_gstin = canonical.get("seller", {}).get("tax_id")
        if seller_gstin:
            if not self._is_valid_gstin(seller_gstin):
                errors.append(f"Invalid seller GSTIN format: {seller_gstin}")
            else:
                seller_state = self._extract_state_code(seller_gstin)
                if seller_state:
                    # Validate state code is valid (01-38 for Indian states)
                    if not (1 <= int(seller_state) <= 38):
                        errors.append(f"Invalid state code in seller GSTIN: {seller_state}")
        
        # Validate buyer GSTIN
        buyer_gstin = canonical.get("buyer", {}).get("tax_id")
        if buyer_gstin:
            if not self._is_valid_gstin(buyer_gstin):
                errors.append(f"Invalid buyer GSTIN format: {buyer_gstin}")
        
        # Validate tax logic (IGST vs CGST/SGST)
        if seller_gstin and buyer_gstin:
            seller_state = self._extract_state_code(seller_gstin)
            buyer_state = self._extract_state_code(buyer_gstin)
            
            if seller_state and buyer_state:
                is_interstate = seller_state != buyer_state
                
                totals = canonical.get("totals", {})
                igst_amount = totals.get("igst", {}).get("amount", 0.0) or 0.0
                cgst_amount = totals.get("cgst", {}).get("amount", 0.0) or 0.0
                sgst_amount = totals.get("sgst", {}).get("amount", 0.0) or 0.0
                
                if is_interstate:
                    # Should have IGST, not CGST/SGST
                    if cgst_amount > 0 or sgst_amount > 0:
                        errors.append(
                            f"Interstate transaction (seller: {seller_state}, buyer: {buyer_state}) "
                            f"should use IGST, not CGST/SGST"
                        )
                    if igst_amount == 0:
                        warnings.append(
                            f"Interstate transaction but no IGST amount found"
                        )
                else:
                    # Should have CGST/SGST, not IGST
                    if igst_amount > 0:
                        errors.append(
                            f"Intrastate transaction (both in state {seller_state}) "
                            f"should use CGST/SGST, not IGST"
                        )
                    if cgst_amount == 0 and sgst_amount == 0:
                        warnings.append(
                            f"Intrastate transaction but no CGST/SGST amounts found"
                        )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _is_valid_gstin(self, gstin: str) -> bool:
        """
        Validate GSTIN format.
        
        GSTIN format: 15 characters
        - 2 digits: State code
        - 10 characters: PAN
        - 1 character: Entity number
        - 1 character: Default 'Z'
        - 1 character: Check digit
        """
        if not gstin or len(gstin) != 15:
            return False
        
        # Check format: 2 digits + 10 alphanumeric + 1 alphanumeric + Z + 1 alphanumeric
        pattern = r'^\d{2}[A-Z0-9]{10}[A-Z0-9]{1}Z[A-Z0-9]{1}$'
        return bool(re.match(pattern, gstin.upper()))
    
    def _extract_state_code(self, gstin: str) -> Optional[str]:
        """Extract state code from GSTIN (first 2 digits)."""
        if not gstin or len(gstin) < 2:
            return None
        return gstin[:2]
