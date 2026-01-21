"""
Context Analyzer - Analyzes invoice and template context.
Detects country, invoice type, field conventions, and regional patterns.
"""
import json
from typing import Dict, Any, Optional

from .ai_client import AIClient


class ContextAnalyzer:
    """
    Analyzes invoice and template context to understand:
    - Country/region (India, US, etc.)
    - Invoice type (GST, VAT, service, etc.)
    - Field conventions (RATE = percentage in India, unit_price in US)
    - Tax structure (CGST/SGST, VAT, sales tax, etc.)
    """
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize context analyzer.
        
        Args:
            ai_client: Optional AI client (creates new one if not provided)
        """
        self.ai_client = ai_client or AIClient()
    
    def analyze_context(
        self,
        canonical_data: Dict[str, Any],
        template_schema: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze context and return context information.
        
        Args:
            canonical_data: Extracted invoice data (canonical model)
            template_schema: Template schema with columns
            document_text: Optional original document text
        
        Returns:
            Context information: {
                "country": "India",
                "invoice_type": "GST",
                "field_conventions": {...},
                ...
            }
        """
        columns = template_schema.get('columns', [])
        column_headers = [col.get('header', '') for col in columns]
        
        # Build context analysis prompt
        prompt = f"""Analyze this invoice and template to understand the context and regional conventions.

Invoice Data (sample):
{json.dumps(canonical_data, indent=2, default=str)[:2000]}

Template Columns:
{json.dumps(column_headers, indent=2)}

Document Text (sample):
{document_text[:1000] if document_text else 'N/A'}

Determine:
1. Country/Region (India, US, UK, etc.) - look for GSTIN, VAT numbers, tax structures, currency
2. Invoice Type (GST invoice, VAT invoice, service invoice, purchase invoice, etc.)
3. Tax Structure (intra-state, inter-state, VAT, sales tax, etc.)
4. Field Conventions - What do these columns mean in this context:
   - What does "RATE" mean? (GST rate percentage in India, unit price in US, etc.)
   - What does "TAXABLE VALUE" mean? (base amount before tax)
   - What do tax fields mean? (CGST/SGST in India, VAT in EU, sales tax in US, etc.)
5. Date Format (DD-MM-YYYY in India, MM-DD-YYYY in US, etc.)
6. Number Format (Indian numbering with commas, US numbering, etc.)
7. Currency (INR, USD, EUR, etc.)
8. Specific Regional Notes (e.g., "In India, RATE column often means GST rate percentage, not unit price")

Return JSON:
{{
  "country": "India",
  "region": "Asia",
  "invoice_type": "GST",
  "tax_structure": "intra_state",
  "field_conventions": {{
    "RATE": "GST rate percentage (e.g., 9%, 18%) - NOT unit price",
    "TAXABLE VALUE": "Base amount before taxes",
    "CGST": "Central GST amount",
    "SGST": "State GST amount",
    "IGST": "Integrated GST (for inter-state transactions)"
  }},
  "date_format": "DD-MM-YYYY",
  "number_format": "Indian",
  "currency": "INR",
  "specific_notes": "In India, RATE column often means GST rate percentage, not unit price. Unit price would be in line_items[].unit_price"
}}"""
        
        try:
            response = self.ai_client.call(
                system_prompt="You are an expert at analyzing invoice context and regional conventions. Analyze invoices to understand country-specific field meanings and tax structures.",
                user_prompt=prompt,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            context = self.ai_client.extract_json(response)
            print(f"🌍 [CONTEXT ANALYZER] Detected: {context.get('country', 'Unknown')} - {context.get('invoice_type', 'Unknown')} invoice")
            print(f"🌍 [CONTEXT ANALYZER] Field conventions: {context.get('field_conventions', {})}")
            
            return context
        except Exception as e:
            print(f"⚠️  [CONTEXT ANALYZER] Context analysis failed: {e}. Using default context.")
            # Return default context (assume India/GST for now)
            return {
                "country": "India",
                "region": "Asia",
                "invoice_type": "GST",
                "tax_structure": "unknown",
                "field_conventions": {
                    "RATE": "Could be GST rate or unit price - analyze data to determine",
                    "TAXABLE VALUE": "Base amount before taxes",
                    "CGST": "Central GST amount",
                    "SGST": "State GST amount"
                },
                "date_format": "DD-MM-YYYY",
                "number_format": "Indian",
                "currency": "INR",
                "specific_notes": "Unable to determine context - use general mapping"
            }
