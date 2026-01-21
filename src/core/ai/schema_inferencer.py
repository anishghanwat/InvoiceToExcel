"""
Schema Inferencer - AI-powered template schema understanding.
Infers column meanings, data types, and mappings from any CSV template.
"""
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .ai_client import AIClient
from .context_analyzer import ContextAnalyzer
from .prompt_generator import PromptGenerator


class SchemaInferencer:
    """
    Infers template schema from CSV headers using AI.
    No assumptions about column names - pure semantic understanding.
    Uses dynamic prompt generation based on context.
    """
    
    def __init__(self, ai_client: Optional[AIClient] = None, use_dynamic_prompts: bool = True):
        """
        Initialize schema inferencer.
        
        Args:
            ai_client: Optional AI client (creates new one if not provided)
            use_dynamic_prompts: Whether to use dynamic prompt generation (default: True)
        """
        self.ai_client = ai_client or AIClient()
        self.use_dynamic_prompts = use_dynamic_prompts
        
        if use_dynamic_prompts:
            self.context_analyzer = ContextAnalyzer(ai_client)
            self.prompt_generator = PromptGenerator(ai_client)
            print("📝 [SCHEMA INFERENCER] Using dynamic prompt generation")
        else:
            self._load_inference_prompt()
            print("📝 [SCHEMA INFERENCER] Using static prompts")
    
    def _load_inference_prompt(self):
        """Load schema inference prompt template."""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "schema_inference_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        else:
            self.prompt_template = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default schema inference prompt."""
        return """You are an expert at analyzing CSV column headers and inferring their semantic meaning.

Your task: Analyze CSV headers and infer complete schema information.

For each header, determine:
1. Semantic meaning (what invoice data it represents)
2. Data type (date, number, text, etc.)
3. Format hints (date format, number precision, etc.)
4. Mapping to canonical invoice model
5. Validation rules (if applicable)

Return JSON schema with complete column definitions."""
    
    def infer_schema(
        self,
        csv_headers: List[str],
        sample_data_rows: Optional[List[Dict[str, str]]] = None,
        canonical_sample: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Infer complete template schema from CSV headers.
        
        Args:
            csv_headers: Column names from user's template
            sample_data_rows: Optional sample data rows for context
            canonical_sample: Optional extracted invoice data for mapping reference
        
        Returns:
            Complete schema with column definitions, types, and mappings
        """
        # Build user prompt
        user_prompt = self._build_inference_prompt(
            csv_headers, sample_data_rows, canonical_sample
        )
        
        # Generate dynamic prompt if enabled
        if self.use_dynamic_prompts and canonical_sample:
            print("🌍 [SCHEMA INFERENCER] Analyzing context...")
            context = self.context_analyzer.analyze_context(
                canonical_sample,
                {"columns": [{"header": h} for h in csv_headers]},
                None
            )
            
            print("📝 [SCHEMA INFERENCER] Generating context-aware prompt...")
            system_prompt = self.prompt_generator.generate_schema_inference_prompt(
                context, csv_headers
            )
        else:
            system_prompt = self.prompt_template
        
        try:
            response = self.ai_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            schema = self.ai_client.extract_json(response)
            
            # Validate and normalize schema
            return self._normalize_schema(schema, csv_headers)
            
        except Exception as e:
            raise Exception(f"Schema inference failed: {str(e)}") from e
    
    def _build_inference_prompt(
        self,
        csv_headers: List[str],
        sample_data_rows: Optional[List[Dict[str, str]]],
        canonical_sample: Optional[Dict[str, Any]]
    ) -> str:
        """Build inference prompt from headers and context."""
        prompt = f"""Analyze these CSV column headers and infer complete schema:

CSV Headers:
{json.dumps(csv_headers, indent=2)}
"""
        
        if sample_data_rows:
            prompt += f"""
Sample Data Rows (for context):
{json.dumps(sample_data_rows[:3], indent=2, default=str)[:1500]}
"""
        
        if canonical_sample:
            prompt += f"""
Available Invoice Data (for mapping reference):
{json.dumps(canonical_sample, indent=2, default=str)[:2000]}
"""
        
        prompt += """
For each header, infer:
1. semantic_type: What invoice data it represents (e.g., "invoice_date", "unit_price", "tax_amount")
2. data_type: "date", "number", "text", "currency", etc.
3. format_hint: Format specification (e.g., "DD-MM-YYYY" for dates, "2" for 2 decimal places)
4. canonical_path: Path in canonical model (e.g., "invoice.invoice_date", "line_items[].unit_price")
5. validation: Optional validation rules

Return JSON schema:
{
  "columns": [
    {
      "header": "Column Name",
      "semantic_type": "invoice_date",
      "data_type": "date",
      "format_hint": "DD-MM-YYYY",
      "canonical_path": "invoice.invoice_date",
      "validation": {...}
    },
    ...
  ]
}"""
        
        return prompt
    
    def _normalize_schema(
        self,
        schema: Dict[str, Any],
        original_headers: List[str]
    ) -> Dict[str, Any]:
        """Normalize and validate inferred schema."""
        columns = schema.get('columns', [])
        
        # Ensure all headers are covered
        header_set = set(original_headers)
        inferred_headers = {col.get('header') for col in columns}
        
        # Add missing headers with default inference
        for header in header_set - inferred_headers:
            columns.append({
                "header": header,
                "semantic_type": "unknown",
                "data_type": "text",
                "canonical_path": f"unknown.{header.lower().replace(' ', '_')}"
            })
        
        # Ensure canonical_path exists for all columns
        for col in columns:
            if 'canonical_path' not in col:
                col['canonical_path'] = self._infer_default_path(col.get('header', ''))
        
        return {
            "name": schema.get('name', 'AI-inferred template'),
            "columns": columns,
            "repeat": schema.get('repeat', None)  # Line item expansion
        }
    
    def _infer_default_path(self, header: str) -> str:
        """Infer default canonical path from header name - AI-driven only."""
        # No hardcoded fallback - return unknown path
        # AI should have inferred the correct path in _normalize_schema
        header_lower = header.lower().replace(' ', '_')
        return f"unknown.{header_lower}"
