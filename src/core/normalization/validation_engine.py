"""
Layer C: Confidence & Validation (NO AI)
Deterministic validation and confidence scoring.
Fast, predictable, no randomness.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class ValidationEngine:
    """Deterministic validation and confidence scoring."""
    
    def __init__(self):
        """Initialize validation engine."""
        self.validation_rules = {
            'math_checks': True,
            'date_checks': True,
            'format_checks': True,
            'required_fields': True
        }
    
    def validate(self, canonical: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate canonical invoice data.
        
        Returns:
            Validation results with confidence scores
        """
        validation_result = {
            'is_valid': True,
            'confidence': 1.0,
            'errors': [],
            'warnings': [],
            'field_confidence': {},
            'math_checks': {},
            'needs_repair': False
        }
        
        # Math validation
        math_result = self._validate_math(canonical)
        validation_result['math_checks'] = math_result
        
        if not math_result['subtotal_tax_total_match']:
            validation_result['errors'].append("Math check failed: subtotal + tax != total")
            validation_result['needs_repair'] = True
            validation_result['is_valid'] = False
        
        # Date validation
        date_result = self._validate_date(canonical.get('invoice_date'))
        if not date_result['is_valid']:
            validation_result['warnings'].append(f"Date validation: {date_result['issue']}")
        
        # Required fields check
        required_fields = ['invoice_number', 'invoice_date', 'total_amount']
        missing_fields = [field for field in required_fields if not canonical.get(field)]
        if missing_fields:
            validation_result['warnings'].append(f"Missing required fields: {', '.join(missing_fields)}")
            if len(missing_fields) >= 2:
                validation_result['needs_repair'] = True
        
        # Field confidence scoring
        validation_result['field_confidence'] = self._calculate_field_confidence(canonical)
        
        # Overall confidence
        validation_result['confidence'] = self._calculate_overall_confidence(
            validation_result['field_confidence'],
            validation_result['math_checks']
        )
        
        return validation_result
    
    def _validate_math(self, canonical: Dict[str, Any]) -> Dict[str, bool]:
        """Validate mathematical relationships."""
        subtotal = canonical.get('subtotal') or 0
        tax_amount = canonical.get('tax_amount') or 0
        total = canonical.get('total_amount') or 0
        
        calculated_total = subtotal + tax_amount
        tolerance = 0.01  # Allow small rounding differences
        
        return {
            'subtotal_tax_total_match': abs(calculated_total - total) <= tolerance,
            'calculated_total': calculated_total,
            'reported_total': total,
            'difference': abs(calculated_total - total)
        }
    
    def _validate_date(self, date_str: Optional[str]) -> Dict[str, Any]:
        """Validate date format and logic."""
        if not date_str:
            return {'is_valid': False, 'issue': 'Date is missing'}
        
        # Check if date is in future (unlikely for invoices)
        # This is a simple check - can be enhanced
        
        return {'is_valid': True, 'issue': None}
    
    def _calculate_field_confidence(self, canonical: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence score for each field."""
        confidence = {}
        
        # High confidence if field exists and looks valid
        for field in ['invoice_number', 'invoice_date', 'vendor', 'customer', 'total_amount']:
            value = canonical.get(field)
            if value:
                if field == 'total_amount':
                    # Amount should be positive
                    confidence[field] = 0.9 if value > 0 else 0.5
                elif field == 'invoice_date':
                    # Date should be parseable
                    confidence[field] = 0.9
                else:
                    confidence[field] = 0.85
            else:
                confidence[field] = 0.0
        
        return confidence
    
    def _calculate_overall_confidence(
        self, 
        field_confidence: Dict[str, float],
        math_checks: Dict[str, Any]
    ) -> float:
        """Calculate overall document confidence."""
        if not field_confidence:
            return 0.0
        
        # Average field confidence
        avg_field_confidence = sum(field_confidence.values()) / len(field_confidence)
        
        # Penalize if math doesn't match
        math_penalty = 0.0 if math_checks.get('subtotal_tax_total_match', False) else 0.2
        
        overall = max(0.0, min(1.0, avg_field_confidence - math_penalty))
        
        return overall
