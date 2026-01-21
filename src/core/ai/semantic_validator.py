"""
Semantic Validator - AI-powered validation using semantic understanding.
No hardcoded business rules - understands invoice context.
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from .ai_client import AIClient


class SemanticValidator:
    """
    Validates invoice data using AI semantic understanding.
    Checks for logical inconsistencies, missing fields, and data quality.
    """
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize semantic validator.
        
        Args:
            ai_client: Optional AI client (creates new one if not provided)
        """
        self.ai_client = ai_client or AIClient()
        self._load_validation_prompt()
    
    def _load_validation_prompt(self):
        """Load validation prompt template."""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "validation_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        else:
            self.prompt_template = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default validation prompt."""
        return """You are an expert invoice validation system.

Your task: Validate invoice data for logical consistency and completeness.

Check for:
1. Logical inconsistencies (e.g., totals don't match, dates are invalid)
2. Missing critical fields (invoice number, date, amounts)
3. Data quality issues (unusual values, format errors)
4. Business rule violations (e.g., tax calculations, rounding)

Return validation results with errors, warnings, and confidence scores."""
    
    def validate_invoice(
        self,
        canonical_data: Dict[str, Any],
        document_text: Optional[str] = None,
        validation_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate invoice data semantically.
        
        Args:
            canonical_data: Extracted invoice data (canonical model)
            document_text: Optional original document text for context
            validation_rules: Optional custom validation rules
        
        Returns:
            Validation results: {
                "valid": bool,
                "errors": [...],
                "warnings": [...],
                "confidence_scores": {...}
            }
        """
        # Build user prompt
        user_prompt = self._build_validation_prompt(
            canonical_data, document_text, validation_rules
        )
        
        # Call AI
        system_prompt = self.prompt_template
        
        try:
            response = self.ai_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            validation_result = self.ai_client.extract_json(response)
            
            # Normalize result
            return self._normalize_validation_result(validation_result)
            
        except Exception as e:
            # Return basic validation if AI fails
            return {
                "valid": True,
                "errors": [],
                "warnings": [f"AI validation unavailable: {str(e)}"],
                "confidence_scores": {}
            }
    
    def _build_validation_prompt(
        self,
        canonical_data: Dict[str, Any],
        document_text: Optional[str],
        validation_rules: Optional[Dict[str, Any]]
    ) -> str:
        """Build validation prompt from data and rules."""
        prompt = f"""Validate this invoice data:

Invoice Data:
{json.dumps(canonical_data, indent=2, default=str)[:3000]}
"""
        
        if document_text:
            prompt += f"""
Original Document Text (for context):
{document_text[:2000]}
"""
        
        if validation_rules:
            prompt += f"""
Custom Validation Rules:
{json.dumps(validation_rules, indent=2)}
"""
        
        prompt += """
Check for:
1. Logical inconsistencies (totals, calculations)
2. Missing critical fields
3. Data quality issues
4. Format errors

Return JSON:
{
  "valid": true/false,
  "errors": ["error1", "error2"],
  "warnings": ["warning1", "warning2"],
  "confidence_scores": {
    "field_name": 0.0-1.0
  }
}"""
        
        return prompt
    
    def _normalize_validation_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validation result structure."""
        return {
            "valid": result.get("valid", True),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "confidence_scores": result.get("confidence_scores", {})
        }
    
    def infer_validation_rules(
        self,
        template_schema: Dict[str, Any],
        sample_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Infer validation rules from template and sample data.
        
        Args:
            template_schema: Template schema
            sample_data: Sample data rows
        
        Returns:
            Inferred validation rules
        """
        prompt = f"""Infer validation rules from this template and sample data:

Template Schema:
{json.dumps(template_schema, indent=2)[:2000]}

Sample Data:
{json.dumps(sample_data[:5], indent=2, default=str)[:2000]}

Return validation rules JSON."""
        
        try:
            response = self.ai_client.call(
                system_prompt="Infer validation rules from template and sample data.",
                user_prompt=prompt,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            return self.ai_client.extract_json(response)
        except Exception:
            return {}
