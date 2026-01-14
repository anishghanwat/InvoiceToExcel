"""
Layer B: AI Semantic Interpretation (CORE AI LAYER)
Uses AI to resolve ambiguous field mappings and select correct values.
This is where AI provides the most value.
"""
import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class AISemanticResolver:
    """
    AI-powered semantic resolver for ambiguous invoice fields.
    Resolves cases where multiple candidates exist for the same field.
    """
    
    def __init__(self, provider: str = "gemini", model: Optional[str] = None):
        """
        Initialize AI semantic resolver.
        
        Args:
            provider: AI provider ('gemini', 'openai', etc.)
            model: Model name
        """
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
                    # Fix model name if needed
                    if '1.5' in self.model and '2.5' not in self.model:
                        self.model = self.model.replace('1.5', '2.5')
                else:
                    self.client = None
            except ImportError:
                self.client = None
    
    def resolve_ambiguous_fields(
        self, 
        canonical: Dict[str, Any],
        candidates: Dict[str, List[Dict[str, Any]]],
        document_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use AI to resolve ambiguous field mappings.
        
        Args:
            canonical: Current canonical mapping (from deterministic layer)
            candidates: Multiple candidate values for ambiguous fields
            document_context: Optional document text for context
            
        Returns:
            Resolved canonical mapping with AI-selected values
        """
        if not self.client or not candidates:
            return canonical, {}
        
        # Only resolve fields that have multiple candidates
        ambiguous_fields = {
            field: values for field, values in candidates.items() 
            if len(values) > 1
        }
        
        if not ambiguous_fields:
            return canonical, {}
        
        try:
            # Build AI prompt
            prompt = self._build_resolution_prompt(ambiguous_fields, canonical, document_context)
            
            # Call AI
            response = self._call_ai(prompt)
            
            # Parse and apply AI decisions
            resolved, field_confidences = self._parse_ai_response(response, canonical, ambiguous_fields)
            
            return resolved, field_confidences
            
        except Exception as e:
            print(f"⚠️  AI resolution failed: {e}. Using deterministic mapping.")
            return canonical, {}
    
    def _build_resolution_prompt(
        self, 
        ambiguous_fields: Dict[str, List[Dict[str, Any]]],
        canonical: Dict[str, Any],
        document_context: Optional[str] = None
    ) -> str:
        """Build production prompt for AI semantic resolution."""
        # Build fields_to_resolve in the exact format specified
        fields_to_resolve = {}
        for field, candidates in ambiguous_fields.items():
            fields_to_resolve[field] = [
                {"label": c.get("label", ""), "value": c.get("value", "")}
                for c in candidates
            ]
        
        # SYSTEM PROMPT (exact as specified)
        system_prompt = """You are an invoice normalization engine.

Your task is to select the most semantically correct value
for each requested invoice field based on business meaning,
not label similarity alone.

Rules:
- Prefer payable / final amounts over subtotals.
- Ignore subtotals unless explicitly marked as final.
- Dates must represent invoice issue date, not due date.
- Invoice number must be unique, not order ID unless specified.
- Return a confidence score between 0 and 1.
- Be deterministic. No explanations unless requested."""
        
        # USER PROMPT (JSON-IN format)
        user_prompt_data = {
            "document_type": "invoice",
            "currency": canonical.get("currency", "USD"),
            "fields_to_resolve": fields_to_resolve
        }
        
        user_prompt = json.dumps(user_prompt_data, indent=2, default=str)
        
        # Combine prompts
        full_prompt = f"""{system_prompt}

{user_prompt}

Return JSON in this exact format:
{{
  "field_name": {{
    "value": <selected_value>,
    "source_label": "<label_of_selected_candidate>",
    "confidence": 0.0-1.0
  }}
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
    
    def _parse_ai_response(
        self, 
        response_text: str,
        canonical: Dict[str, Any],
        ambiguous_fields: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Parse AI response in exact production format."""
        resolved = canonical.copy()
        field_confidences = {}
        
        try:
            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Apply resolutions (exact format: field_name -> {value, source_label, confidence})
            for field, resolution in result.items():
                if field in resolved or field in ambiguous_fields:
                    value = resolution.get("value")
                    confidence = resolution.get("confidence", 0.5)
                    source_label = resolution.get("source_label", "")
                    
                    # Only apply if confidence is high enough
                    if confidence > 0.7 and value is not None:
                        # Map field names to canonical schema
                        canonical_field = self._map_to_canonical_field(field)
                        if canonical_field:
                            resolved[canonical_field] = value
                            field_confidences[canonical_field] = confidence
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"⚠️  Failed to parse AI response: {e}")
        
        return resolved, field_confidences
    
    def _map_to_canonical_field(self, field: str) -> Optional[str]:
        """Map field name to canonical schema field."""
        mapping = {
            "total_amount": "total_amount",
            "invoice_date": "invoice_date",
            "invoice_number": "invoice_number",
            "vendor": "vendor",
            "customer": "customer",
            "subtotal": "subtotal",
            "tax_amount": "tax_amount",
            "tax_rate": "tax_rate"
        }
        return mapping.get(field)
    
    def collect_candidates(self, results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect all candidate values for fields that might be ambiguous.
        
        Returns:
            Dict mapping field names to list of candidate {label, value} dicts
        """
        candidates = {
            'total_amount': [],
            'subtotal': [],
            'tax_amount': [],
            'tax_rate': [],
            'invoice_date': [],
            'invoice_number': [],
            'vendor': [],
            'customer': []
        }
        
        # Collect from key-value pairs
        for kv in results.get('key_value_pairs', []):
            key = kv['key'].strip()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            key_lower = key.lower()
            
            # Categorize candidates
            if any(word in key_lower for word in ['total', 'grand total', 'amount due', 'total payable']):
                amount = self._extract_amount(value)
                if amount is not None:
                    candidates['total_amount'].append({'label': key, 'value': amount})
            
            elif any(word in key_lower for word in ['subtotal', 'total (excl']):
                amount = self._extract_amount(value)
                if amount is not None:
                    candidates['subtotal'].append({'label': key, 'value': amount})
            
            elif any(word in key_lower for word in ['tax', 'vat', 'gst']) and 'rate' not in key_lower:
                amount = self._extract_amount(value)
                if amount is not None:
                    candidates['tax_amount'].append({'label': key, 'value': amount})
            
            elif any(word in key_lower for word in ['tax rate', 'vat rate', 'gst rate']):
                rate = self._extract_percentage(value)
                if rate is not None:
                    candidates['tax_rate'].append({'label': key, 'value': rate})
            
            elif any(word in key_lower for word in ['date', 'dated']):
                candidates['invoice_date'].append({'label': key, 'value': value})
            
            elif any(word in key_lower for word in ['invoice', 'inv no', 'bill no']):
                candidates['invoice_number'].append({'label': key, 'value': value})
            
            elif any(word in key_lower for word in ['vendor', 'supplier', 'sold by', 'from']):
                candidates['vendor'].append({'label': key, 'value': value})
            
            elif any(word in key_lower for word in ['customer', 'bill to', 'to', 'buyer']):
                candidates['customer'].append({'label': key, 'value': value})
        
        # Remove empty candidate lists
        return {k: v for k, v in candidates.items() if v}
    
    def _extract_amount(self, value: str) -> Optional[float]:
        """Extract amount from value string."""
        cleaned = re.sub(r'[£$€₹Rs\.rs\.,\s]', '', str(value))
        if cleaned.startswith('.'):
            cleaned = '0' + cleaned
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _extract_percentage(self, value: str) -> Optional[float]:
        """Extract percentage from value string."""
        cleaned = value.replace('%', '').strip()
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
