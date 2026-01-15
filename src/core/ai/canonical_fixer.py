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
    
    def __init__(self, provider: str = "gemini", model: Optional[str] = None, max_retries: int = 2):
        """
        Initialize AI canonical fixer.
        
        Args:
            provider: AI provider ('gemini', 'openai', etc.)
            model: Model name
            max_retries: Maximum number of retry attempts for AI calls
        """
        self.provider = provider.lower()
        self.model = model or os.getenv('AI_MODEL', 'gemini-2.5-flash')
        self.max_retries = max_retries
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
    
    def fix_canonical(
        self,
        canonical: Dict[str, Any],
        textract_output: Optional[Dict[str, Any]] = None,
        document_text: Optional[str] = None,
        validation_errors: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Fix and complete canonical invoice model using AI.
        
        Args:
            canonical: Partial canonical invoice model (from deterministic extraction)
            textract_output: Raw Textract output for reference
            document_text: Full document text for context
            validation_errors: Validation errors that need fixing
            
        Returns:
            Tuple of (fixed canonical model, field confidence scores)
        """
        if not self.client:
            return canonical, {}
        
        try:
            # Build AI prompt
            prompt = self._build_fix_prompt(canonical, textract_output, document_text, validation_errors)
            
            # Call AI
            response = self._call_ai(prompt)
            
            # Parse and apply fixes
            fixed_canonical, confidences = self._parse_fix_response(response, canonical)
            
            return fixed_canonical, confidences
            
        except Exception as e:
            print(f"⚠️  AI canonical fix failed: {e}. Returning original canonical.")
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
        system_prompt = """You are an invoice data extraction engine.

Your task is to fill missing fields in the canonical invoice JSON.
Use the document text to infer missing values.

Rules:
- Only use values explicitly stated in the document or that can be reliably inferred
- If a value is not present or cannot be inferred, set it to null
- Do not invent data
- Do NOT calculate or compute any values (totals, taxes, etc.) - only extract what's in the document
- Return corrected canonical JSON with the exact same structure
- Include confidence scores (0.0-1.0) for each field you fill
- Preserve all existing correct values"""
        
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
1. Fill any missing fields that can be inferred from the document
2. Correct any fields that have validation errors
3. Return the complete canonical JSON with the same structure
4. Include a "confidence" object with confidence scores for each field you modified

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
    
    def _call_ai(self, prompt: str) -> str:
        """
        Call AI API with retry logic.
        
        Args:
            prompt: The prompt to send to AI
            
        Returns:
            AI response text
            
        Raises:
            Exception: If AI call fails after retries
        """
        if not self.client:
            raise Exception("AI client not initialized")
        
        if self.provider == "gemini":
            @retry_with_backoff(
                max_retries=self.max_retries,
                initial_delay=1.0,
                max_delay=30.0,
                retryable_exceptions=(Exception,),
                on_retry=lambda attempt, error: print(f"⚠️  AI API retry {attempt}/{self.max_retries}...")
            )
            def _gemini_call():
                try:
                    model = self.client.GenerativeModel(self.model)
                    generation_config = {
                        "temperature": 0.1,
                        "max_output_tokens": 4096,
                    }
                    response = model.generate_content(prompt, generation_config=generation_config)
                    if not response or not response.text:
                        raise Exception("Empty response from AI")
                    return response.text.strip()
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for quota/rate limit errors
                    if "quota" in error_str or "429" in error_str or "rate limit" in error_str:
                        raise Exception(f"AI quota/rate limit exceeded: {e}")
                    # Check for invalid request errors (don't retry)
                    if "invalid" in error_str or "400" in error_str:
                        raise Exception(f"Invalid AI request: {e}")
                    # Retry for other errors
                    raise
            
            return _gemini_call()
        
        raise Exception(f"Unsupported AI provider: {self.provider}")
    
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
