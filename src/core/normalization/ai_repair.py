"""
Layer D: AI Repair / Self-Correction (SECONDARY AI)
Only runs when validation fails or confidence is low.
Uses AI to fix errors and infer missing fields.
"""
import os
import json
import re
from typing import Dict, List, Any, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class AIRepair:
    """
    AI-powered repair for invoice data errors.
    Only invoked when validation fails or confidence is low.
    """
    
    def __init__(self, provider: str = "gemini", model: Optional[str] = None):
        """Initialize AI repair."""
        self.provider = provider.lower()
        self.model = model or os.getenv('AI_MODEL', 'gemini-2.5-flash')
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize AI client."""
        if self.provider == "gemini":
            try:
                import google.generativeai as genai
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.client = genai
                    if '1.5' in self.model and '2.5' not in self.model:
                        self.model = self.model.replace('1.5', '2.5')
                else:
                    self.client = None
            except ImportError:
                self.client = None
    
    def repair(
        self,
        canonical: Dict[str, Any],
        validation_result: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> tuple[Dict[str, Any], Dict[str, float]]:
        """
        Repair invoice data using AI.
        
        Args:
            canonical: Current canonical data (may have errors)
            validation_result: Validation results showing what's wrong
            document_text: Document text for context
            
        Returns:
            Repaired canonical data
        """
        if not self.client:
            return canonical
        
        # Only repair if needed
        if not validation_result.get('needs_repair', False):
            return canonical
        
        try:
            # Build repair prompt
            prompt = self._build_repair_prompt(canonical, validation_result, document_text)
            
            # Call AI
            response = self._call_ai(prompt)
            
            # Parse and apply repairs
            repaired = self._parse_repair_response(response, canonical)
            
            return repaired
            
        except Exception as e:
            print(f"⚠️  AI repair failed: {e}. Returning original data.")
            return canonical
    
    def _build_repair_prompt(
        self,
        canonical: Dict[str, Any],
        validation_result: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> str:
        """Build production prompt for AI repair (exact format)."""
        # SYSTEM PROMPT (exact as specified)
        system_prompt = """You are an invoice data repair engine.

You are given extracted values that failed validation.
Use the document text to correct them.
Prefer values explicitly stated in the document.
Return corrected value and confidence."""
        
        # Build error context
        errors = validation_result.get('errors', [])
        math_checks = validation_result.get('math_checks', {})
        
        # USER PROMPT (exact format)
        if math_checks and not math_checks.get('subtotal_tax_total_match', True):
            user_prompt_data = {
                "error": "subtotal + tax != total",
                "values": {
                    "subtotal": canonical.get('subtotal', 0),
                    "tax": canonical.get('tax_amount', 0),
                    "total": canonical.get('total_amount', 0)
                },
                "document_snippet": document_text[:500] if document_text else ""
            }
        else:
            user_prompt_data = {
                "error": "; ".join(errors) if errors else "validation_failed",
                "values": {
                    "invoice_number": canonical.get('invoice_number'),
                    "invoice_date": canonical.get('invoice_date'),
                    "total": canonical.get('total_amount')
                },
                "document_snippet": document_text[:500] if document_text else ""
            }
        
        user_prompt = json.dumps(user_prompt_data, indent=2, default=str)
        
        # Combine prompts
        full_prompt = f"""{system_prompt}

{user_prompt}

Return JSON in this exact format:
{{
  "corrected_total": <number> | null,
  "corrected_subtotal": <number> | null,
  "corrected_tax": <number> | null,
  "corrected_invoice_date": "<YYYY-MM-DD>" | null,
  "corrected_invoice_number": "<string>" | null,
  "confidence": 0.0-1.0
}}

IMPORTANT: Only return JSON, no other text."""
        
        return full_prompt
    
    def _call_ai(self, prompt: str) -> str:
        """Call AI API."""
        if self.provider == "gemini" and self.client:
            model = self.client.GenerativeModel(self.model)
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 2048,
            }
            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text.strip()
        return ""
    
    def _parse_repair_response(
        self,
        response_text: str,
        canonical: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI repair response in exact production format."""
        repaired = canonical.copy()
        repair_confidences = {}
        
        try:
            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Apply corrections (exact format)
            if result.get("corrected_total") is not None:
                repaired["total_amount"] = result["corrected_total"]
                repair_confidences["total_amount"] = result.get("confidence", 0.5)
                print(f"   🔧 Repaired total_amount: {canonical.get('total_amount')} → {result['corrected_total']}")
            
            if result.get("corrected_subtotal") is not None:
                repaired["subtotal"] = result["corrected_subtotal"]
                repair_confidences["subtotal"] = result.get("confidence", 0.5)
            
            if result.get("corrected_tax") is not None:
                repaired["tax_amount"] = result["corrected_tax"]
                repair_confidences["tax_amount"] = result.get("confidence", 0.5)
            
            if result.get("corrected_invoice_date"):
                repaired["invoice_date"] = result["corrected_invoice_date"]
                repair_confidences["invoice_date"] = result.get("confidence", 0.5)
            
            if result.get("corrected_invoice_number"):
                repaired["invoice_number"] = result["corrected_invoice_number"]
                repair_confidences["invoice_number"] = result.get("confidence", 0.5)
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"⚠️  Failed to parse repair response: {e}")
        
        return repaired, repair_confidences
