"""
Main Validation Engine - Orchestrates all validators.
"""
from typing import Dict, Any
from .gst import GSTValidator
from .math import MathValidator


class ValidationEngine:
    """
    Main validation engine that runs all validators.
    
    Validates canonical invoice model before export.
    If validation fails, flags row and allows user correction.
    """
    
    def __init__(self):
        """Initialize validation engine."""
        self.gst_validator = GSTValidator()
        self.math_validator = MathValidator()
    
    def validate(self, canonical: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all validators on canonical invoice model.
        
        Args:
            canonical: Canonical invoice model
            
        Returns:
            Combined validation result
        """
        # Run all validators
        gst_result = self.gst_validator.validate(canonical)
        math_result = self.math_validator.validate(canonical)
        
        # Combine results
        all_errors = gst_result.get("errors", []) + math_result.get("errors", [])
        all_warnings = gst_result.get("warnings", []) + math_result.get("warnings", [])
        
        return {
            "valid": len(all_errors) == 0,
            "needs_repair": len(all_errors) > 0,
            "errors": all_errors,
            "warnings": all_warnings,
            "gst": gst_result,
            "math": math_result
        }
