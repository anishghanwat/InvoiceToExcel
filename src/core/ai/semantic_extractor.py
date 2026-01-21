"""
Semantic Extractor - AI-driven field extraction from Textract output.
No keyword matching - pure semantic understanding.
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path

from .ai_client import AIClient
from .context_analyzer import ContextAnalyzer
from .prompt_generator import PromptGenerator


class SemanticExtractor:
    """
    Extracts invoice data using AI semantic understanding.
    Replaces hardcoded keyword matching with intelligent extraction.
    """
    
    def __init__(self, ai_client: Optional[AIClient] = None, use_dynamic_prompts: bool = True):
        """
        Initialize semantic extractor.
        
        Args:
            ai_client: Optional AI client (creates new one if not provided)
        """
        self.ai_client = ai_client or AIClient()
        self.use_dynamic_prompts = use_dynamic_prompts
        
        if use_dynamic_prompts:
            self.context_analyzer = ContextAnalyzer(ai_client)
            self.prompt_generator = PromptGenerator(ai_client)
            print("📝 [SEMANTIC EXTRACTOR] Using dynamic prompt generation")
        else:
            self._load_extraction_prompt()
            print("📝 [SEMANTIC EXTRACTOR] Using static prompts")
    
    def _load_extraction_prompt(self):
        """Load extraction prompt template."""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "extraction_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        else:
            # Default prompt if file doesn't exist
            self.prompt_template = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default extraction prompt."""
        return """You are an expert invoice data extraction system.

Your task: Extract ALL invoice data from the provided document using semantic understanding.

Key Principles:
1. Understand MEANING, not keywords - extract data based on what it represents
2. Extract EVERY field you can find - be comprehensive
3. Handle variations intelligently (e.g., "Rate", "Unit Price", "Cost" all = unit_price)
4. Only extract values explicitly stated in the document - do not calculate
5. Return complete canonical invoice JSON structure

Extract ALL fields including:
- Invoice details (number, date, due date, order number)
- Seller/buyer information (names, addresses, tax IDs, GSTIN)
- Line items (description, HSN, quantity, unit_price, taxable_value, taxes)
- Totals (taxable_value, CGST/SGST/IGST amounts, round_off, total)
- Metadata (ledger, payment terms, notes)

Return ONLY valid JSON in the canonical invoice structure."""
    
    def extract_all_fields(
        self,
        textract_results: Dict[str, Any],
        document_text: Optional[str] = None,
        base_canonical: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all invoice fields using AI semantic understanding.
        
        Args:
            textract_results: Raw Textract output (text_blocks, key_value_pairs, tables)
            document_text: Optional full document text for context
            base_canonical: Optional base canonical structure to merge into
        
        Returns:
            Complete canonical invoice model
        """
        print("🔍 [SEMANTIC EXTRACTOR] Starting extraction...")
        
        # Start with base structure if provided, otherwise create empty
        if base_canonical is None:
            from src.core.normalize.canonical_schema import CanonicalSchema
            base_canonical = CanonicalSchema.create_empty()
            print("🔍 [SEMANTIC EXTRACTOR] Created empty base canonical structure")
        else:
            print(f"🔍 [SEMANTIC EXTRACTOR] Using provided base canonical (has {len(base_canonical)} top-level keys)")
        
        # Prepare input data
        if not document_text:
            document_text = self._extract_full_text(textract_results)
            print(f"🔍 [SEMANTIC EXTRACTOR] Extracted document text: {len(document_text)} chars")
        
        # Check Textract data
        kv_pairs_count = len(textract_results.get('key_value_pairs', []))
        tables_count = len(textract_results.get('tables', []))
        text_blocks_count = len(textract_results.get('text_blocks', []))
        print(f"🔍 [SEMANTIC EXTRACTOR] Textract data: {kv_pairs_count} KV pairs, {tables_count} tables, {text_blocks_count} text blocks")
        
        # Build user prompt with canonical schema
        user_prompt = self._build_extraction_prompt(textract_results, document_text, base_canonical)
        print(f"🔍 [SEMANTIC EXTRACTOR] Built prompt: {len(user_prompt)} chars")
        
        # Generate dynamic prompt if enabled
        if self.use_dynamic_prompts:
            # Analyze context from textract results and document text
            print("🌍 [SEMANTIC EXTRACTOR] Analyzing context...")
            # Create a minimal canonical sample for context analysis
            context_sample = base_canonical.copy() if base_canonical else {}
            context = self.context_analyzer.analyze_context(
                context_sample,
                {"columns": []},  # No template schema needed for extraction
                document_text
            )
            
            print("📝 [SEMANTIC EXTRACTOR] Generating context-aware prompt...")
            system_prompt = self.prompt_generator.generate_extraction_prompt(
                context, document_text
            )
        else:
            system_prompt = self.prompt_template
        
        print("🔍 [SEMANTIC EXTRACTOR] Calling AI...")
        
        try:
            response = self.ai_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            print(f"🔍 [SEMANTIC EXTRACTOR] AI response received: {len(response)} chars")
            print(f"🔍 [SEMANTIC EXTRACTOR] AI response preview: {response[:500]}...")
            
            # Parse JSON response
            ai_response = self.ai_client.extract_json(response)
            print(f"🔍 [SEMANTIC EXTRACTOR] Parsed JSON: {len(ai_response)} top-level keys")
            print(f"🔍 [SEMANTIC EXTRACTOR] AI response keys: {list(ai_response.keys())}")
            
            # Check what data AI extracted
            if 'invoice' in ai_response:
                invoice_data = ai_response.get('invoice', {})
                print(f"🔍 [SEMANTIC EXTRACTOR] Invoice data: {list(invoice_data.keys())}")
                if invoice_data.get('invoice_number'):
                    print(f"🔍 [SEMANTIC EXTRACTOR] Found invoice_number: {invoice_data.get('invoice_number')}")
            
            if 'buyer' in ai_response:
                buyer_data = ai_response.get('buyer', {})
                print(f"🔍 [SEMANTIC EXTRACTOR] Buyer data: {list(buyer_data.keys())}")
                if buyer_data.get('name'):
                    print(f"🔍 [SEMANTIC EXTRACTOR] Found buyer name: {buyer_data.get('name')}")
            
            if 'totals' in ai_response:
                totals_data = ai_response.get('totals', {})
                print(f"🔍 [SEMANTIC EXTRACTOR] Totals data: {list(totals_data.keys())}")
                if totals_data.get('total'):
                    print(f"🔍 [SEMANTIC EXTRACTOR] Found total: {totals_data.get('total')}")
            
            # Merge AI response into base structure (ensures valid structure)
            print("🔍 [SEMANTIC EXTRACTOR] Merging AI response into base canonical...")
            canonical = self._merge_ai_response(base_canonical, ai_response)
            
            # Check merged result
            print(f"🔍 [SEMANTIC EXTRACTOR] Merged canonical keys: {list(canonical.keys())}")
            if canonical.get('invoice', {}).get('invoice_number'):
                print(f"🔍 [SEMANTIC EXTRACTOR] Merged invoice_number: {canonical['invoice']['invoice_number']}")
            if canonical.get('buyer', {}).get('name'):
                print(f"🔍 [SEMANTIC EXTRACTOR] Merged buyer name: {canonical['buyer']['name']}")
            if canonical.get('totals', {}).get('total'):
                print(f"🔍 [SEMANTIC EXTRACTOR] Merged total: {canonical['totals']['total']}")
            
            # Guard against empty extraction
            invoice_number = canonical.get('invoice', {}).get('invoice_number')
            buyer_name = canonical.get('buyer', {}).get('name')
            totals_total = canonical.get('totals', {}).get('total')
            line_items = canonical.get('line_items', [])
            if not invoice_number and not buyer_name and totals_total in (None, "") and len(line_items) == 0:
                raise ValueError("Semantic extraction returned empty canonical (no invoice_number, buyer, totals, or line_items).")
            
            print("✅ [SEMANTIC EXTRACTOR] Extraction complete")
            return canonical
            
        except Exception as e:
            # Log what AI returned for debugging
            print(f"❌ [SEMANTIC EXTRACTOR] Error: {str(e)}")
            try:
                if 'response' in locals():
                    print(f"❌ [SEMANTIC EXTRACTOR] AI Response (first 500 chars): {str(response)[:500]}")
            except:
                pass
            import traceback
            print(f"❌ [SEMANTIC EXTRACTOR] Traceback: {traceback.format_exc()}")
            raise Exception(f"Semantic extraction failed: {str(e)}") from e
    
    def _extract_full_text(self, textract_results: Dict[str, Any]) -> str:
        """Extract full document text from Textract results."""
        text_parts = []
        
        # Add text blocks
        for block in textract_results.get('text_blocks', []):
            if isinstance(block, dict) and 'text' in block:
                text_parts.append(block['text'])
            elif isinstance(block, str):
                text_parts.append(block)
        
        # Add key-value pairs
        for kv in textract_results.get('key_value_pairs', []):
            if isinstance(kv, dict):
                key = kv.get('key', '')
                value = kv.get('value', '')
                if key and value:
                    text_parts.append(f"{key}: {value}")
        
        # Add tables
        for table in textract_results.get('tables', []):
            if isinstance(table, list):
                for row in table:
                    if isinstance(row, list):
                        text_parts.append(' | '.join(str(cell) for cell in row))
        
        return '\n'.join(text_parts)
    
    def _build_extraction_prompt(
        self,
        textract_results: Dict[str, Any],
        document_text: str,
        canonical_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build extraction prompt from Textract results."""
        # Prepare structured data for AI
        kv_pairs = textract_results.get('key_value_pairs', [])[:50]  # Limit size
        tables = textract_results.get('tables', [])[:5]  # Limit size
        
        # Create simplified schema example for AI
        schema_example = {
            "invoice": {
                "invoice_number": "string or null",
                "invoice_date": "date string or null",
                "due_date": "date string or null"
            },
            "buyer": {
                "name": "string or null",
                "tax_id": "GSTIN string or null"
            },
            "line_items": [
                {
                    "description": "string",
                    "quantity": "number",
                    "unit_price": "number",
                    "taxable_value": "number"
                }
            ],
            "totals": {
                "taxable_value": "number or null",
                "cgst": {"amount": "number or null"},
                "sgst": {"amount": "number or null"},
                "igst": {"amount": "number or null"},
                "round_off": "number or null",
                "total": "number or null"
            },
            "metadata": {
                "ledger": "string or null"
            }
        }
        
        prompt = f"""Extract ALL invoice data from this document.

Document Text:
{document_text[:5000]}

Key-Value Pairs (from Textract):
{json.dumps(kv_pairs, indent=2, default=str)[:2000]}

Tables (from Textract):
{json.dumps(tables, indent=2, default=str)[:2000]}

Target Structure (return data in this format - fill what you can find, use null for missing):
{json.dumps(schema_example, indent=2)[:1500]}

Extract semantically - understand what each field means, not just match keywords.
Return JSON with extracted values. You can return partial data - missing fields will be null.
Important: Return valid JSON that matches the structure above."""
        
        return prompt
    
    def _merge_ai_response(
        self,
        base: Dict[str, Any],
        ai_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge AI response into base canonical structure.
        Ensures we always have a valid structure even if AI returns partial data.
        """
        print(f"🔍 [MERGE] Starting merge: base has {len(base)} keys, AI response has {len(ai_response)} keys")
        
        def merge_dict(base_dict: Dict, ai_dict: Dict, path: str = "") -> Dict:
            """Recursively merge dictionaries."""
            result = base_dict.copy()
            merged_count = 0
            for key, value in ai_dict.items():
                current_path = f"{path}.{key}" if path else key
                if key in result:
                    if isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = merge_dict(result[key], value, current_path)
                        merged_count += 1
                    elif isinstance(result[key], list) and isinstance(value, list):
                        result[key] = value  # Replace list entirely
                        print(f"🔍 [MERGE] Replaced list at {current_path}: {len(value)} items")
                        merged_count += 1
                    elif value is not None:
                        result[key] = value
                        print(f"🔍 [MERGE] Set {current_path} = {value}")
                        merged_count += 1
                else:
                    # AI returned a field not in base structure - add it to metadata or ignore
                    # For now, we'll add it to metadata.notes if it's a string
                    if isinstance(value, str) and 'metadata' in result and isinstance(result.get('metadata'), dict):
                        if result['metadata'].get('notes'):
                            result['metadata']['notes'] += f"; {key}: {value}"
                        else:
                            result['metadata']['notes'] = f"{key}: {value}"
                        print(f"🔍 [MERGE] Added unknown field {key} to metadata.notes")
            
            if merged_count > 0:
                print(f"🔍 [MERGE] Merged {merged_count} fields at {path or 'root'}")
            return result
        
        merged = merge_dict(base, ai_response)
        print(f"🔍 [MERGE] Merge complete. Result has {len(merged)} top-level keys")
        return merged
    
    def _is_valid_canonical(self, data: Dict[str, Any]) -> bool:
        """Validate canonical structure - more lenient."""
        # Just check if it's a dict - we'll merge into base structure anyway
        return isinstance(data, dict)
