"""
AI-powered CSV mapper using LLMs for intelligent column matching.
Supports OpenAI, Anthropic Claude, and local models via Ollama.
"""
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher


class AIMapper:
    """AI-powered mapper that uses LLMs for intelligent column matching."""
    
    def __init__(self, provider: str = "gemini", model: Optional[str] = None):
        """
        Initialize AI mapper.
        
        Args:
            provider: AI provider ('gemini', 'openai', 'anthropic', 'ollama', or 'none' for fallback)
            model: Model name (optional, uses defaults if not provided)
        """
        self.provider = provider.lower()
        self.model = model
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the AI client based on provider."""
        if self.provider == "gemini":
            try:
                import google.generativeai as genai
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.client = genai
                    # Use model from env or default - ensure correct model name
                    env_model = os.getenv('AI_MODEL', 'gemini-2.5-flash')
                    self.model = self.model or env_model
                    # Fix common wrong model names
                    if '1.5' in self.model and '2.5' not in self.model:
                        self.model = self.model.replace('1.5', '2.5')
                    print(f"✅ Gemini AI initialized (model: {self.model})")
                else:
                    print("⚠️  Gemini API key not found. Set GEMINI_API_KEY in .env file.")
                    print("   Get free API key at: https://makersuite.google.com/app/apikey")
                    self.provider = "none"
            except ImportError:
                print("⚠️  google-generativeai package not installed. Install with: pip install google-generativeai")
                self.provider = "none"
        
        elif self.provider == "openai":
            try:
                import openai
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    self.client = openai.OpenAI(api_key=api_key)
                    self.model = self.model or "gpt-4o-mini"
                else:
                    print("⚠️  OpenAI API key not found. Falling back to rule-based mapping.")
                    self.provider = "none"
            except ImportError:
                print("⚠️  openai package not installed. Install with: pip install openai")
                self.provider = "none"
        
        elif self.provider == "anthropic":
            try:
                import anthropic
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    self.client = anthropic.Anthropic(api_key=api_key)
                    self.model = self.model or "claude-3-haiku-20240307"
                else:
                    print("⚠️  Anthropic API key not found. Falling back to rule-based mapping.")
                    self.provider = "none"
            except ImportError:
                print("⚠️  anthropic package not installed. Install with: pip install anthropic")
                self.provider = "none"
        
        elif self.provider == "ollama":
            try:
                import ollama
                self.client = ollama
                self.model = self.model or "llama3.2"
            except ImportError:
                print("⚠️  ollama package not installed. Install with: pip install ollama")
                self.provider = "none"
        
        else:
            self.provider = "none"
    
    def map_columns_intelligently(
        self, 
        columns: List[str], 
        table_headers: List[List[str]], 
        sample_data: Optional[Dict[str, Any]] = None,
        sample_rows: Optional[List[List[List[str]]]] = None
    ) -> Dict[str, Tuple[int, int]]:
        """
        Use AI to intelligently map user columns to table column indices.
        
        Args:
            columns: User-defined column names
            table_headers: List of table headers (one per table)
            sample_data: Optional sample data for context
            
        Returns:
            Dict mapping user columns to (table_index, column_index) tuples
        """
        if self.provider == "none":
            return self._fallback_mapping(columns, table_headers)
        
        try:
            if self.provider == "gemini":
                return self._map_with_gemini(columns, table_headers, sample_data, sample_rows)
            elif self.provider == "openai":
                return self._map_with_openai(columns, table_headers, sample_data, sample_rows)
            elif self.provider == "anthropic":
                return self._map_with_anthropic(columns, table_headers, sample_data, sample_rows)
            elif self.provider == "ollama":
                return self._map_with_ollama(columns, table_headers, sample_data, sample_rows)
        except Exception as e:
            print(f"⚠️  AI mapping failed: {e}. Falling back to rule-based mapping.")
            return self._fallback_mapping(columns, table_headers)
    
    def _map_with_gemini(self, columns: List[str], table_headers: List[List[str]], sample_data: Optional[Dict] = None, sample_rows: Optional[List[List[List[str]]]] = None) -> Dict[str, Tuple[int, int]]:
        """Map columns using Google Gemini API."""
        import google.generativeai as genai
        
        prompt = self._build_mapping_prompt(columns, table_headers, sample_data, sample_rows)
        
        model = genai.GenerativeModel(self.model)
        
        # Configure generation for JSON output
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response if it's wrapped
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Return empty result if can't parse
                return {}
        return self._parse_ai_response(result, columns, table_headers)
    
    def _map_with_openai(self, columns: List[str], table_headers: List[List[str]], sample_data: Optional[Dict] = None, sample_rows: Optional[List[List[List[str]]]] = None) -> Dict[str, Tuple[int, int]]:
        """Map columns using OpenAI API."""
        prompt = self._build_mapping_prompt(columns, table_headers, sample_data, sample_rows)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at mapping invoice data to CSV columns. Analyze table headers and match them to user-requested columns with high accuracy."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent results
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return self._parse_ai_response(result, columns, table_headers)
    
    def _map_with_anthropic(self, columns: List[str], table_headers: List[List[str]], sample_data: Optional[Dict] = None, sample_rows: Optional[List[List[List[str]]]] = None) -> Dict[str, Tuple[int, int]]:
        """Map columns using Anthropic Claude API."""
        prompt = self._build_mapping_prompt(columns, table_headers, sample_data, sample_rows)
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.1,
            system="You are an expert at mapping invoice data to CSV columns. Analyze table headers and match them to user-requested columns with high accuracy.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        result = json.loads(message.content[0].text)
        return self._parse_ai_response(result, columns, table_headers)
    
    def _map_with_ollama(self, columns: List[str], table_headers: List[List[str]], sample_data: Optional[Dict] = None, sample_rows: Optional[List[List[List[str]]]] = None) -> Dict[str, Tuple[int, int]]:
        """Map columns using Ollama (local model)."""
        prompt = self._build_mapping_prompt(columns, table_headers, sample_data, sample_rows)
        
        response = self.client.generate(
            model=self.model,
            prompt=f"System: You are an expert at mapping invoice data to CSV columns.\n\nUser: {prompt}\n\nRespond with valid JSON only.",
            options={"temperature": 0.1}
        )
        
        result = json.loads(response['response'])
        return self._parse_ai_response(result, columns, table_headers)
    
    def _build_mapping_prompt(self, columns: List[str], table_headers: List[List[str]], sample_data: Optional[Dict] = None, sample_rows: Optional[List[List[List[str]]]] = None) -> str:
        """Build the prompt for AI mapping."""
        prompt = f"""You are an expert at mapping invoice table data to CSV columns. Analyze the table structure and map user-requested columns accurately.

USER-REQUESTED COLUMNS: {json.dumps(columns, indent=2)}

AVAILABLE TABLES:
"""
        for table_idx, headers in enumerate(table_headers):
            if not headers:
                continue
            prompt += f"\n--- Table {table_idx} ---\n"
            prompt += f"Headers: {json.dumps(headers, indent=2)}\n"
            
            # Include sample data rows if available
            if sample_rows and table_idx < len(sample_rows):
                table_data = sample_rows[table_idx]
                if len(table_data) > 1:
                    prompt += f"\nSample data rows (first 3):\n"
                    for row_idx, row in enumerate(table_data[1:4], 1):  # Skip header, show first 3 rows
                        prompt += f"  Row {row_idx}: {json.dumps(row, indent=2)}\n"
        
        prompt += f"""

MAPPING RULES:
1. Match user columns to table columns based on semantic meaning, not just text similarity
2. Common mappings:
   - "sr.no", "sr no", "serial no", "sno" → column with row numbers or serial numbers
   - "particulars", "description", "product", "item" → column with product/item descriptions
   - "qty", "quantity" → column with quantities (numbers)
   - "rate", "unit price", "price" → column with unit prices
   - "amount", "subtotal", "total" → column with line item totals (not grand total)
   - "tax", "vat" → column with tax rates or tax amounts
   - "date" → column with dates
   - "invoice_no", "invoice number" → column with invoice numbers

3. IMPORTANT: 
   - Only map to data columns (not summary/total rows)
   - Prefer columns that contain actual line item data
   - Avoid mapping to empty columns or header-only columns
   - If multiple tables exist, prefer the table with line items (has Description, Qty, Price columns)

4. Return ONLY valid mappings with confidence > 0.7

Return JSON in this exact format:
{{
  "mappings": {{
    "column_name": {{"table": 0, "column": 2}},
    ...
  }},
  "confidence": {{
    "column_name": 0.95
  }},
  "reasoning": {{
    "column_name": "Brief explanation of why this mapping was chosen"
  }}
}}

IMPORTANT: Return ONLY the JSON object, no other text.
"""
        return prompt
    
    def _parse_ai_response(self, result: Dict, columns: List[str], table_headers: List[List[str]]) -> Dict[str, Tuple[int, int]]:
        """Parse AI response and validate mappings."""
        mappings = {}
        
        if "mappings" not in result:
            return self._fallback_mapping(columns, table_headers)
        
        for col_name, mapping_info in result["mappings"].items():
            if col_name not in columns:
                continue
            
            table_idx = mapping_info.get("table", 0)
            col_idx = mapping_info.get("column", -1)
            confidence = result.get("confidence", {}).get(col_name, 0.5)
            
            # Validate indices
            if 0 <= table_idx < len(table_headers):
                if 0 <= col_idx < len(table_headers[table_idx]):
                    if confidence > 0.7:  # Only use high-confidence matches
                        mappings[col_name] = (table_idx, col_idx)
        
        return mappings
    
    def _fallback_mapping(self, columns: List[str], table_headers: List[List[str]]) -> Dict[str, Tuple[int, int]]:
        """Fallback to rule-based mapping when AI is not available."""
        mappings = {}
        
        for col_idx, user_col in enumerate(columns):
            user_col_lower = user_col.lower()
            best_match = None
            best_score = 0
            
            for table_idx, headers in enumerate(table_headers):
                for header_idx, header in enumerate(headers):
                    header_lower = header.lower()
                    
                    # Calculate similarity
                    if user_col_lower == header_lower:
                        score = 1.0
                    elif user_col_lower in header_lower or header_lower in user_col_lower:
                        score = 0.8
                    else:
                        score = SequenceMatcher(None, user_col_lower, header_lower).ratio()
                    
                    if score > best_score and score > 0.6:
                        best_score = score
                        best_match = (table_idx, header_idx)
            
            if best_match:
                mappings[user_col] = best_match
        
        return mappings
    
    def validate_and_correct_mapping(
        self, 
        mappings: Dict[str, List[str]], 
        columns: List[str],
        sample_rows: Optional[List[List[str]]] = None
    ) -> Dict[str, List[str]]:
        """
        Use AI to validate and correct column mappings.
        
        Args:
            mappings: Current column mappings
            columns: Column names
            sample_rows: Sample data rows for validation
            
        Returns:
            Corrected mappings
        """
        if self.provider == "none" or not sample_rows:
            return mappings
        
        try:
            prompt = f"""Review these CSV column mappings for an invoice and correct any errors:

Columns: {json.dumps(columns)}

Current mappings (first 3 values per column):
{json.dumps({k: v[:3] for k, v in mappings.items()}, indent=2)}

Sample data rows:
{json.dumps(sample_rows[:5] if sample_rows else [], indent=2)}

Identify and fix:
1. Wrong data types (e.g., amounts in description column)
2. Misaligned data (e.g., quantities in amount column)
3. Missing or empty columns that should have data
4. Duplicate or redundant mappings

Return JSON with corrected mappings and explanations:
{{
  "corrections": {{
    "column_name": {{
      "action": "replace|remove|reorder",
      "values": ["new", "values"],
      "reason": "Explanation"
    }}
  }}
}}
"""
            
            if self.provider == "gemini":
                import google.generativeai as genai
                model = genai.GenerativeModel(self.model)
                generation_config = {
                    "temperature": 0.1,
                    "max_output_tokens": 2048,
                }
                response = model.generate_content(prompt, generation_config=generation_config)
                response_text = response.text.strip()
                
                # Extract JSON if wrapped in markdown
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    # Try to extract JSON from response if it's wrapped
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        # Return original mappings if can't parse
                        return mappings
                except json.JSONDecodeError as e:
                    # Try to extract JSON from response if it's wrapped
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        raise e
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
            else:
                # For other providers, return original mappings
                return mappings
            
            # Apply corrections
            corrected = mappings.copy()
            if "corrections" in result:
                for col_name, correction in result["corrections"].items():
                    if col_name in corrected:
                        action = correction.get("action", "replace")
                        if action == "replace" and "values" in correction:
                            corrected[col_name] = correction["values"]
                        elif action == "remove":
                            corrected[col_name] = []
            
            return corrected
            
        except Exception as e:
            print(f"⚠️  AI validation failed: {e}")
            return mappings
