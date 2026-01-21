"""
Unified AI Client - Handles OpenAI and Gemini with fallback.
Provides a consistent interface for all AI operations.
"""
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class AIClient:
    """
    Unified AI client for OpenAI (primary) and Gemini (fallback).
    Provides consistent interface for all AI operations.
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize AI client with auto-detection.
        
        Args:
            provider: 'openai' or 'gemini'. If None, auto-detects (OpenAI first).
        """
        self.provider = provider or self._auto_detect_provider()
        self.primary_client = None
        self.fallback_client = None
        self.primary_model = None
        self.fallback_model = None
        
        self._initialize_clients()
    
    def _auto_detect_provider(self) -> str:
        """Auto-detect provider based on available API keys."""
        openai_key = os.getenv('OPENAI_API_KEY', '')
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        
        if openai_key and openai_key != 'your_openai_api_key_here' and openai_key.strip():
            return 'openai'
        elif gemini_key and gemini_key != 'your_gemini_api_key_here' and gemini_key.strip():
            return 'gemini'
        else:
            raise ValueError("No AI provider available. Please set OPENAI_API_KEY or GEMINI_API_KEY")
    
    def _initialize_clients(self):
        """Initialize primary and fallback AI clients."""
        # Initialize primary (OpenAI)
        if self.provider == 'openai' or not self.provider:
            try:
                from openai import OpenAI
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key and api_key != 'your_openai_api_key_here' and api_key.strip():
                    self.primary_client = OpenAI(api_key=api_key)
                    self.primary_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            except ImportError:
                pass
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI: {e}")
        
        # Initialize fallback (Gemini)
        try:
            import google.generativeai as genai
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key and api_key != 'your_gemini_api_key_here' and api_key.strip():
                genai.configure(api_key=api_key)
                self.fallback_client = genai
                self.fallback_model = os.getenv('AI_MODEL', 'gemini-2.0-flash-exp')
                if '1.5' in self.fallback_model and '2.0' not in self.fallback_model:
                    self.fallback_model = self.fallback_model.replace('1.5', '2.0')
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  Failed to initialize Gemini fallback: {e}")
    
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Call AI with unified interface.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature (0.0-1.0)
            max_tokens: Max tokens (None = default)
            response_format: Optional response format (e.g., {"type": "json_object"})
        
        Returns:
            AI response text
        
        Raises:
            Exception: If all providers fail
        """
        # Try primary first
        if self.primary_client:
            try:
                return self._call_openai(
                    system_prompt, user_prompt, temperature, max_tokens, response_format
                )
            except Exception as e:
                print(f"⚠️  OpenAI call failed: {e}. Trying fallback...")
        
        # Fallback to Gemini
        if self.fallback_client:
            try:
                return self._call_gemini(
                    system_prompt, user_prompt, temperature, max_tokens
                )
            except Exception as e:
                print(f"⚠️  Gemini call failed: {e}")
        
        raise Exception("All AI providers failed")
    
    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict[str, Any]]
    ) -> str:
        """Call OpenAI API."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        params = {
            "model": self.primary_model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        if response_format:
            params["response_format"] = response_format
        
        response = self.primary_client.chat.completions.create(**params)
        
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        
        raise Exception("OpenAI returned empty response")
    
    def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> str:
        """Call Gemini API."""
        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        model = self.fallback_client.GenerativeModel(self.fallback_model)
        
        generation_config = {
            "temperature": temperature,
        }
        
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            return response.text.strip()
        
        raise Exception("Gemini returned empty response")
    
    def extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from AI response (handles markdown code blocks).
        
        Args:
            text: AI response text
        
        Returns:
            Parsed JSON dictionary
        """
        # Remove markdown code blocks
        text = text.strip()
        if text.startswith("```"):
            # Extract content between ```json and ```
            lines = text.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            text = '\n'.join(lines)
        
        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Could not extract JSON from response: {text[:200]}")
