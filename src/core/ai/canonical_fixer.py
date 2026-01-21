"""
AI Canonical Fixer - AI works ONLY with canonical JSON.

This is the accuracy layer. AI should never see CSVs.
AI input: Raw Textract output + Partial canonical object + Validation rules
AI output: Canonical JSON ONLY (strict schema, confidence scores)
"""
import os
import json
import re
import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.utils.retry import retry_with_backoff

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class CanonicalFixer:
    """
    AI-powered fixer for canonical invoice model.
    
    This is where AI provides accuracy. It:
    - Fills missing fields in canonical JSON
    - Corrects errors in canonical JSON
    - Never sees or cares about CSV formats
    """
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, max_retries: int = 2):
        """
        Initialize AI canonical fixer.
        
        Args:
            provider: AI provider ('openai', 'gemini', etc.). If None, auto-detects based on available API keys (OpenAI first, then Gemini)
            model: Model name (defaults based on provider)
            max_retries: Maximum number of retry attempts for AI calls
        """
        self.max_retries = max_retries
        self.client = None
        self.fallback_client = None
        self.provider = None
        self.fallback_provider = None
        self.model = None
        self.fallback_model = None
        
        # Auto-detect provider if not specified
        if provider is None:
            provider = self._auto_detect_provider()
        
        self.provider = provider.lower()
        self._initialize_clients()
    
    def _auto_detect_provider(self) -> str:
        """Auto-detect provider based on available API keys (OpenAI first, then Gemini)."""
        openai_key = os.getenv('OPENAI_API_KEY')
        gemini_key = os.getenv('GEMINI_API_KEY')
        
        # Check if keys are not just placeholders
        if openai_key and openai_key != 'your_openai_api_key_here' and openai_key.strip():
            return "openai"
        elif gemini_key and gemini_key != 'your_gemini_api_key_here' and gemini_key.strip():
            return "gemini"
        else:
            # Default to gemini if neither is available (for backward compatibility)
            return "gemini"
    
    def _initialize_clients(self):
        """Initialize primary and fallback AI clients."""
        # Initialize primary provider
        if self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key and api_key != 'your_openai_api_key_here' and api_key.strip():
                    # Store OpenAI client instance
                    self.client = OpenAI(api_key=api_key)
                    self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
                else:
                    self.client = None
            except ImportError:
                print("⚠️  OpenAI package not installed. Install with: pip install openai")
                self.client = None
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI client: {e}")
                self.client = None
            
            # Initialize Gemini as fallback
            try:
                import google.generativeai as genai
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key and api_key != 'your_gemini_api_key_here' and api_key.strip():
                    genai.configure(api_key=api_key)
                    self.fallback_client = genai
                    self.fallback_provider = "gemini"
                    fallback_model = os.getenv('AI_MODEL', 'gemini-2.5-flash')
                    if '1.5' in fallback_model and '2.5' not in fallback_model:
                        fallback_model = fallback_model.replace('1.5', '2.5')
                    self.fallback_model = fallback_model
                else:
                    self.fallback_client = None
            except ImportError:
                self.fallback_client = None
            except Exception as e:
                print(f"⚠️  Failed to initialize Gemini fallback client: {e}")
                self.fallback_client = None
                
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key and api_key != 'your_gemini_api_key_here' and api_key.strip():
                    genai.configure(api_key=api_key)
                    self.client = genai
                    self.model = os.getenv('AI_MODEL', 'gemini-2.5-flash')
                    if '1.5' in self.model and '2.5' not in self.model:
                        self.model = self.model.replace('1.5', '2.5')
                else:
                    self.client = None
            except ImportError:
                self.client = None
            except Exception as e:
                print(f"⚠️  Failed to initialize Gemini client: {e}")
                self.client = None
    
    def fix_canonical(
        self,
        canonical: Dict[str, Any],
        textract_output: Optional[Dict[str, Any]] = None,
        document_text: Optional[str] = None,
        validation_errors: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Fix and complete canonical invoice model using AI.
        Uses primary provider (OpenAI) first, falls back to Gemini if primary fails.
        
        Args:
            canonical: Partial canonical invoice model (from deterministic extraction)
            textract_output: Raw Textract output for reference
            document_text: Full document text for context
            validation_errors: Validation errors that need fixing
            
        Returns:
            Tuple of (fixed canonical model, field confidence scores)
        """
        if not self.client and not self.fallback_client:
            return canonical, {}
        
        # Build AI prompt
        prompt = self._build_fix_prompt(canonical, textract_output, document_text, validation_errors)
        
        # Try primary provider first
        if self.client:
            try:
                response = self._call_ai(prompt, use_fallback=False)
                fixed_canonical, confidences = self._parse_fix_response(response, canonical)
                return fixed_canonical, confidences
            except Exception as e:
                print(f"⚠️  Primary AI provider ({self.provider}) failed: {e}")
                if self.fallback_client:
                    print(f"🔄 Falling back to {self.fallback_provider}...")
                else:
                    print(f"⚠️  No fallback available. Returning original canonical.")
                    return canonical, {}
        
        # Try fallback provider
        if self.fallback_client:
            try:
                response = self._call_ai(prompt, use_fallback=True)
                fixed_canonical, confidences = self._parse_fix_response(response, canonical)
                return fixed_canonical, confidences
            except Exception as e:
                print(f"⚠️  Fallback AI provider ({self.fallback_provider}) also failed: {e}")
                return canonical, {}
        
        return canonical, {}
    
    def _build_fix_prompt(
        self,
        canonical: Dict[str, Any],
        textract_output: Optional[Dict[str, Any]],
        document_text: Optional[str],
        validation_errors: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for AI to fix canonical model.
        
        Key principle: AI fills missing fields in canonical JSON.
        If a value is not present or cannot be inferred, set it to null.
        Do not invent data.
        """
        system_prompt = """You are a deterministic invoice data extraction engine.

Task: Fill missing fields in the canonical invoice JSON by extracting data from the invoice document.

This is invoice-to-CSV data extraction. Extract invoice data fields from the document text.

Extraction Rules (deterministic):
1. Extract ONLY values explicitly stated in the document
2. Do NOT calculate, compute, or infer values (no math operations)
3. If a field is not in the document, set it to null
4. Preserve all existing correct values
5. Return canonical JSON with exact same structure
6. Include confidence scores (0.0-1.0) for extracted fields

Fields to Extract (if present in document):
- Invoice: invoice_number, invoice_date, due_date, order_number
- Seller: name, tax_id (GSTIN), address, pan
- Buyer: name, tax_id (GSTIN), address, pan
- Line Items: description, hsn, quantity, unit_price, taxable_value, taxes (cgst/sgst/igst rates and amounts)
- Totals: taxable_value, cgst.amount, sgst.amount, igst.amount, round_off, total
- Metadata: ledger (if mentioned in document)

Important: Extract unit_price (not "rate") for line items. Extract round_off and ledger if they appear in the document."""
        
        # Build context
        context_parts = []
        
        if document_text:
            context_parts.append(f"Document Text (first 1000 chars):\n{document_text[:1000]}")
        
        if validation_errors:
            errors = validation_errors.get('errors', [])
            if errors:
                context_parts.append(f"Validation Errors:\n{json.dumps(errors, indent=2)}")
        
        context = "\n\n".join(context_parts) if context_parts else "No additional context available."
        
        # Current canonical (as JSON)
        canonical_json = json.dumps(canonical, indent=2, default=str)
        
        user_prompt = f"""Current Canonical Invoice JSON:
{canonical_json}

{context}

Please:
1. COMPREHENSIVELY fill ALL missing fields that can be inferred from the document - be thorough!
2. Extract EVERY possible field including: rates, round off, ledger, complete addresses, all tax details
3. For line items:
   - If unit_price is missing but taxable_value and quantity exist, calculate: unit_price = taxable_value / quantity
   - If quantity is missing but unit_price and taxable_value exist, calculate: quantity = taxable_value / unit_price
   - Look for rate/price information in table headers, descriptions, or nearby text
4. For round_off: Look for "Round Off", "Round", "Rounding", or any small adjustment amounts near totals
5. For ledger: Look for "Ledger", "Account", "Account Name", "GL Code", or similar accounting references
6. Correct any fields that have validation errors
7. Return the complete canonical JSON with the same structure
8. Include a "confidence" object with confidence scores for each field you modified
9. Focus on extracting: invoice details, seller/buyer info, line items with rates/unit_price, all tax fields, totals including round off, and metadata like ledger

Return JSON in this exact format (IMPORTANT: Return valid JSON only, no markdown, no code blocks):
{{
  "canonical": {{
    "invoice": {{ ... }},
    "seller": {{ ... }},
    "buyer": {{ ... }},
    "line_items": [ ... ],
    "totals": {{ ... }}
  }},
  "confidence": {{
    "field_name": 0.0-1.0
  }}
}}

CRITICAL REQUIREMENTS:
- Return ONLY valid JSON, no markdown code blocks
- No explanations or text before or after the JSON
- Ensure all strings are properly escaped
- Ensure all braces and brackets are properly closed
- Do not include comments in JSON"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    def _call_ai(self, prompt: str, use_fallback: bool = False) -> str:
        """
        Call AI API with retry logic.
        
        Args:
            prompt: The prompt to send to AI
            use_fallback: Whether to use fallback provider (default: False, uses primary)
            
        Returns:
            AI response text
            
        Raises:
            Exception: If AI call fails after retries
        """
        if use_fallback:
            client = self.fallback_client
            provider = self.fallback_provider
            model = self.fallback_model
        else:
            client = self.client
            provider = self.provider
            model = self.model
        
        if not client:
            raise Exception(f"AI client not initialized for provider: {provider}")
        
        if provider == "openai":
            @retry_with_backoff(
                max_retries=self.max_retries,
                initial_delay=1.0,
                max_delay=30.0,
                retryable_exceptions=(Exception,),
                on_retry=lambda attempt, error: print(f"⚠️  OpenAI API retry {attempt}/{self.max_retries}...")
            )
            def _openai_call():
                try:
                    # Client is already initialized in __init__
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an invoice data extraction engine. Return only valid JSON, no markdown, no code blocks."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=4096
                    )
                    
                    if not response or not response.choices or not response.choices[0].message.content:
                        raise Exception("Empty response from OpenAI")
                    
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for quota/rate limit errors
                    if "quota" in error_str or "429" in error_str or "rate limit" in error_str:
                        raise Exception(f"OpenAI quota/rate limit exceeded: {e}")
                    # Check for invalid request errors (don't retry)
                    if "invalid" in error_str or "400" in error_str or "401" in error_str:
                        raise Exception(f"Invalid OpenAI request: {e}")
                    # Retry for other errors
                    raise
            
            return _openai_call()
        
        elif provider == "gemini":
            @retry_with_backoff(
                max_retries=self.max_retries,
                initial_delay=1.0,
                max_delay=30.0,
                retryable_exceptions=(Exception,),
                on_retry=lambda attempt, error: print(f"⚠️  Gemini API retry {attempt}/{self.max_retries}...")
            )
            def _gemini_call():
                try:
                    model_obj = client.GenerativeModel(model)
                    generation_config = {
                        "temperature": 0.1,
                        "max_output_tokens": 4096,
                    }
                    response = model_obj.generate_content(prompt, generation_config=generation_config)
                    if not response or not response.text:
                        raise Exception("Empty response from Gemini")
                    return response.text.strip()
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for quota/rate limit errors
                    if "quota" in error_str or "429" in error_str or "rate limit" in error_str:
                        raise Exception(f"Gemini quota/rate limit exceeded: {e}")
                    # Check for invalid request errors (don't retry)
                    if "invalid" in error_str or "400" in error_str:
                        raise Exception(f"Invalid Gemini request: {e}")
                    # Retry for other errors
                    raise
            
            return _gemini_call()
        
        raise Exception(f"Unsupported AI provider: {provider}")
    
    def _parse_fix_response(
        self,
        response_text: str,
        original_canonical: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Parse AI response and merge with original canonical.
        
        Returns:
            Tuple of (fixed canonical, confidence scores)
        """
        fixed = original_canonical.copy()
        confidences = {}
        
        try:
            # Extract JSON from response (handle multiple formats)
            json_text = self._extract_json_from_response(response_text)
            
            if not json_text:
                print("⚠️  No JSON found in AI response, skipping AI fixes")
                return fixed, confidences
            
            # Try to parse JSON
            result = json.loads(json_text)
            
            # Merge canonical
            if "canonical" in result:
                fixed = self._deep_merge(fixed, result["canonical"])
            
            # Extract confidence scores
            if "confidence" in result:
                confidences = result["confidence"]
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse AI fix response: {e}")
            # Try to recover partial JSON
            try:
                result = self._try_recover_json(response_text)
                if result and "canonical" in result:
                    fixed = self._deep_merge(fixed, result["canonical"])
                if result and "confidence" in result:
                    confidences = result["confidence"]
            except Exception as e2:
                print(f"⚠️  JSON recovery also failed: {e2}")
        
        except (KeyError, TypeError) as e:
            print(f"⚠️  Error processing AI fix response: {e}")
        
        return fixed, confidences
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from AI response, handling various formats.
        
        Returns:
            Extracted JSON string or empty string if not found
        """
        if not response_text:
            return ""
        
        # Clean up the response text
        response_text = response_text.strip()
        
        # Try to find JSON in code blocks first
        if "```json" in response_text:
            parts = response_text.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0].strip()
                if json_part:
                    return json_part
        
        if "```" in response_text:
            parts = response_text.split("```")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0].strip()
                # Check if it looks like JSON
                if json_part and (json_part.startswith("{") or json_part.startswith("[")):
                    return json_part
        
        # Try to find JSON object directly
        # Look for first { and try to find matching }
        start_idx = response_text.find("{")
        if start_idx >= 0:
            # Try to find the matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(response_text)):
                char = response_text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_candidate = response_text[start_idx:i+1]
                            # Validate it's valid JSON
                            try:
                                json.loads(json_candidate)
                                return json_candidate
                            except json.JSONDecodeError:
                                # Try to fix common issues and retry
                                fixed = self._fix_common_json_issues(json_candidate)
                                try:
                                    json.loads(fixed)
                                    return fixed
                                except json.JSONDecodeError:
                                    pass
        
        # If we still haven't found valid JSON, try the whole response
        if response_text.startswith("{") or response_text.startswith("["):
            try:
                json.loads(response_text)
                return response_text
            except json.JSONDecodeError:
                # Try fixing common issues
                fixed = self._fix_common_json_issues(response_text)
                try:
                    json.loads(fixed)
                    return fixed
                except json.JSONDecodeError:
                    pass
        
        return ""
    
    def _fix_common_json_issues(self, json_text: str) -> str:
        """
        Fix common JSON formatting issues.
        
        Returns:
            Fixed JSON string
        """
        # Remove trailing commas before } or ]
        fixed = re.sub(r',\s*}', '}', json_text)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # Fix unescaped newlines in strings (basic attempt)
        # This is tricky, so we'll be conservative
        lines = fixed.split('\n')
        result_lines = []
        in_string = False
        
        for line in lines:
            # Simple heuristic: if line has odd number of quotes and we're in a string context
            # This is a basic fix - more complex cases might need more sophisticated parsing
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _try_recover_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Try to recover JSON from malformed response.
        
        Returns:
            Parsed JSON dict or None if recovery fails
        """
        # Try to fix common JSON issues
        # Remove trailing commas
        fixed = re.sub(r',\s*}', '}', response_text)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # Try to fix unterminated strings by finding the JSON object boundaries
        # Look for the main JSON object
        start = fixed.find('{')
        if start >= 0:
            # Try to find a reasonable end point
            # Count braces to find matching closing brace
            brace_count = 0
            end = start
            for i in range(start, min(start + 10000, len(fixed))):  # Limit search
                if fixed[i] == '{':
                    brace_count += 1
                elif fixed[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if end > start:
                json_candidate = fixed[start:end]
                try:
                    return json.loads(json_candidate)
                except json.JSONDecodeError:
                    pass
        
        return None
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        Updates base with values from updates, but only if updates has non-null values.
        """
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            elif value is not None:  # Only update if value is not null
                result[key] = value
        
        return result
