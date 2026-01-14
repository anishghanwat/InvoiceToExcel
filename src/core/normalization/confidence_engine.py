"""
Confidence Scoring Engine (NO AI)
Critical for enterprise trust - most competitors fake confidence.
"""
from typing import Dict, Any, Optional


class ConfidenceEngine:
    """Deterministic confidence scoring - no AI, fully auditable."""
    
    # Field weights for overall confidence
    REQUIRED_FIELD_WEIGHTS = {
        "total": 0.40,
        "invoice_date": 0.25,
        "vendor_name": 0.20,
        "invoice_id": 0.15
    }
    
    # Confidence thresholds
    THRESHOLD_AUTO_APPROVE = 0.9
    THRESHOLD_SOFT_WARNING = 0.8
    THRESHOLD_REVIEW_REQUIRED = 0.8
    
    def calculate_field_confidence(
        self,
        field: str,
        ai_confidence: Optional[float],
        validation_success: bool,
        vendor_pattern_match: float = 0.0
    ) -> float:
        """
        Calculate field-level confidence using exact formula:
        Field Confidence = (AI confidence × 0.6) + (Validation success × 0.25) + (Vendor pattern match × 0.15)
        """
        ai_score = (ai_confidence or 0.0) * 0.6
        validation_score = (1.0 if validation_success else 0.0) * 0.25
        vendor_score = vendor_pattern_match * 0.15
        
        return min(1.0, max(0.0, ai_score + validation_score + vendor_score))
    
    def calculate_overall_confidence(
        self,
        field_confidences: Dict[str, float],
        required_fields: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate overall document confidence using weighted average of required fields.
        
        Required fields:
        - total (40%)
        - invoice_date (25%)
        - vendor_name (20%)
        - invoice_id (15%)
        """
        if not required_fields:
            required_fields = self.REQUIRED_FIELD_WEIGHTS
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for field, weight in required_fields.items():
            # Map field names
            mapped_field = self._map_field_name(field)
            confidence = field_confidences.get(mapped_field, 0.0)
            
            weighted_sum += confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _map_field_name(self, field: str) -> str:
        """Map field name to canonical schema field."""
        mapping = {
            "total": "total_amount",
            "invoice_date": "invoice_date",
            "vendor_name": "vendor",
            "invoice_id": "invoice_number"
        }
        return mapping.get(field, field)
    
    def get_confidence_level(self, confidence: float) -> str:
        """Get confidence level description."""
        if confidence >= self.THRESHOLD_AUTO_APPROVE:
            return "auto_approve"
        elif confidence >= self.THRESHOLD_SOFT_WARNING:
            return "soft_warning"
        else:
            return "review_required"
    
    def calculate_field_confidences(
        self,
        canonical: Dict[str, Any],
        ai_confidences: Dict[str, float],
        validation_result: Dict[str, Any],
        vendor_pattern_match: float = 0.0
    ) -> Dict[str, float]:
        """Calculate confidence for all fields."""
        field_confidences = {}
        math_valid = validation_result.get("math_checks", {}).get("subtotal_tax_total_match", False)
        
        # Required fields
        required_fields = ["total_amount", "invoice_date", "vendor", "invoice_number"]
        
        for field in required_fields:
            ai_conf = ai_confidences.get(field)
            validation_success = True  # Default
            
            if field == "total_amount":
                validation_success = math_valid
            
            field_conf = self.calculate_field_confidence(
                field,
                ai_conf,
                validation_success,
                vendor_pattern_match
            )
            field_confidences[field] = field_conf
        
        return field_confidences
