"""
Prompt Generator - Generates customized prompts based on context.
Instead of hardcoded prompts, creates context-specific instructions.
"""
import json
from typing import Dict, List, Any, Optional

from .ai_client import AIClient


class PromptGenerator:
    """
    Generates customized prompts based on context.
    Creates context-specific instructions for AI operations.
    """
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize prompt generator.
        
        Args:
            ai_client: Optional AI client (creates new one if not provided)
        """
        self.ai_client = ai_client or AIClient()
    
    def generate_mapping_prompt(
        self,
        context: Dict[str, Any],
        template_schema: Dict[str, Any],
        discovered_relationships: str
    ) -> str:
        """
        Generate a customized mapping prompt based on context.
        
        Args:
            context: Context information from ContextAnalyzer
            template_schema: Template schema with columns
            discovered_relationships: Discovered relationships from data analysis
        
        Returns:
            Customized system prompt for mapping
        """
        country = context.get('country', 'Unknown')
        invoice_type = context.get('invoice_type', 'Unknown')
        field_conventions = context.get('field_conventions', {})
        specific_notes = context.get('specific_notes', '')
        tax_structure = context.get('tax_structure', 'Unknown')
        
        columns = template_schema.get('columns', [])
        column_headers = [col.get('header', '') for col in columns]
        
        # Build prompt generation request
        prompt = f"""Generate a customized system prompt for mapping invoice data to template columns.

CONTEXT:
- Country: {country}
- Region: {context.get('region', 'Unknown')}
- Invoice Type: {invoice_type}
- Tax Structure: {tax_structure}
- Currency: {context.get('currency', 'Unknown')}
- Date Format: {context.get('date_format', 'Unknown')}
- Number Format: {context.get('number_format', 'Unknown')}

FIELD CONVENTIONS (country-specific meanings):
{json.dumps(field_conventions, indent=2)}

SPECIFIC NOTES:
{specific_notes}

TEMPLATE COLUMNS:
{json.dumps(column_headers, indent=2)}

DISCOVERED RELATIONSHIPS FROM DATA:
{discovered_relationships}

Generate a system prompt that:
1. Understands {country}-specific conventions (e.g., in {country}, RATE might mean: {field_conventions.get('RATE', 'unit price or tax rate')})
2. Provides accurate field mapping guidance based on {country} invoice conventions
3. Includes discovered relationships from the data analysis
4. Guides the AI to extract values correctly from canonical model
5. Handles {tax_structure} tax structures and calculations
6. Understands that field meanings may differ by country (e.g., RATE = GST percentage in India, unit price in US)
7. Provides clear instructions for each template column based on context

The prompt should be:
- Clear and specific to {country} invoices
- Include field convention explanations
- Reference discovered relationships
- Guide correct value extraction
- Handle country-specific tax calculations

Return ONLY the system prompt text (no JSON wrapper, no markdown, just the prompt text that will be used as system_prompt):"""
        
        try:
            response = self.ai_client.call(
                system_prompt="You are an expert at generating AI prompts for invoice data mapping. Generate clear, context-aware, country-specific prompts that guide AI to map invoice data correctly.",
                user_prompt=prompt,
                temperature=0.2
            )
            
            generated_prompt = response.strip()
            print(f"📝 [PROMPT GENERATOR] Generated {len(generated_prompt)} char prompt for {country} {invoice_type} invoice")
            print(f"📝 [PROMPT GENERATOR] Prompt preview: {generated_prompt[:200]}...")
            
            return generated_prompt
        except Exception as e:
            print(f"⚠️  [PROMPT GENERATOR] Prompt generation failed: {e}. Using fallback prompt.")
            # Fallback to context-aware prompt
            return self._generate_fallback_prompt(context, field_conventions, discovered_relationships)
    
    def _generate_fallback_prompt(
        self,
        context: Dict[str, Any],
        field_conventions: Dict[str, str],
        discovered_relationships: str
    ) -> str:
        """Generate fallback prompt if AI generation fails."""
        country = context.get('country', 'Unknown')
        
        prompt = f"""You are an expert at mapping invoice data to template columns for {country} invoices.

Your task: Map canonical invoice data to template columns semantically. YOU MUST RETURN A VALUE FOR EVERY SINGLE COLUMN IN THE TEMPLATE.

COUNTRY-SPECIFIC CONVENTIONS:
{json.dumps(field_conventions, indent=2)}

DISCOVERED RELATIONSHIPS:
{discovered_relationships}

Key Principles:
1. YOU MUST MAP ALL COLUMNS - Return a value (or null) for every column in the template, no exceptions
2. Understand {country}-specific field meanings (see FIELD CONVENTIONS above)
3. DO NOT copy the same value to multiple columns - each column represents a different field
4. NEVER INVENT OR HALLUCINATE VALUES. Only use values present in the canonical data or derived via discovered relationships. If missing, return null.
5. Do NOT fabricate parties, invoice numbers, dates, GSTINs, or amounts.
6. Use discovered relationships to understand calculations and patterns
7. Extract values directly from canonical model - don't copy values between columns
8. EXCEPTION: CGST and SGST can be equal (intra-state transactions split tax equally)

Return mapped values for each template column."""
        
        return prompt
    
    def generate_extraction_prompt(
        self,
        context: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> str:
        """
        Generate customized extraction prompt based on context.
        
        Args:
            context: Context information
            document_text: Optional document text sample
        
        Returns:
            Customized system prompt for extraction
        """
        country = context.get('country', 'Unknown')
        invoice_type = context.get('invoice_type', 'Unknown')
        tax_structure = context.get('tax_structure', 'Unknown')
        
        prompt = f"""Generate a customized system prompt for extracting invoice data from documents.

CONTEXT:
- Country: {country}
- Invoice Type: {invoice_type}
- Tax Structure: {tax_structure}
- Currency: {context.get('currency', 'Unknown')}
- Date Format: {context.get('date_format', 'Unknown')}

Generate a system prompt that:
1. Understands {country} invoice formats and structures
2. Knows what fields to extract for {invoice_type} invoices
3. Understands {tax_structure} tax calculations
4. Handles {country}-specific date and number formats
5. Extracts all invoice data comprehensively

Return ONLY the system prompt text:"""
        
        try:
            response = self.ai_client.call(
                system_prompt="You are an expert at generating AI prompts for invoice data extraction. Generate clear, context-aware prompts.",
                user_prompt=prompt,
                temperature=0.2
            )
            return response.strip()
        except Exception:
            return f"""You are an expert invoice data extraction system for {country} {invoice_type} invoices.

Your task: Extract ALL invoice data from the provided document using semantic understanding.

Key Principles:
1. Understand MEANING, not keywords - extract data based on what it represents
2. Extract EVERY field you can find - be comprehensive
3. Handle {country}-specific formats and conventions
4. Only extract values explicitly stated in the document - do not calculate
5. Return complete canonical invoice JSON structure"""
    
    def generate_schema_inference_prompt(
        self,
        context: Dict[str, Any],
        csv_headers: List[str]
    ) -> str:
        """
        Generate customized schema inference prompt based on context.
        
        Args:
            context: Context information
            csv_headers: CSV column headers to analyze
        
        Returns:
            Customized system prompt for schema inference
        """
        country = context.get('country', 'Unknown')
        field_conventions = context.get('field_conventions', {})
        
        prompt = f"""Generate a customized system prompt for inferring CSV template schema.

CONTEXT:
- Country: {country}
- Field Conventions: {json.dumps(field_conventions, indent=2)}

CSV Headers to Analyze:
{json.dumps(csv_headers, indent=2)}

Generate a system prompt that:
1. Understands {country}-specific column name meanings
2. Knows field conventions for {country} invoices
3. Can infer semantic types based on {country} invoice standards
4. Understands tax structures and field relationships

Return ONLY the system prompt text:"""
        
        try:
            response = self.ai_client.call(
                system_prompt="You are an expert at generating AI prompts for schema inference. Generate clear, context-aware prompts.",
                user_prompt=prompt,
                temperature=0.2
            )
            return response.strip()
        except Exception:
            return f"""You are an expert at analyzing CSV column headers for {country} invoices and inferring their semantic meaning.

Your task: Analyze CSV headers and infer complete schema information.

For each header, determine:
1. Semantic meaning (what invoice data it represents in {country} context)
2. Data type (date, number, text, percentage, etc.)
3. Format hints (date format, number precision, etc.)
4. Mapping to canonical invoice model
5. Validation rules (if applicable)

Consider {country}-specific conventions when inferring meanings.

Return JSON schema with complete column definitions."""
