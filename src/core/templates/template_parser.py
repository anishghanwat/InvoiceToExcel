"""
Template Parser - Reads user-defined template configurations.

Templates are pure configuration, not code.
A template defines:
- Columns
- Mapping rules (JSONPath to canonical model)
- Optional transforms
- Row expansion rules (for line items)

Supports both JSON and CSV template files.
Uses AI-powered mapping for intelligent header-to-path matching.
"""
import json
import csv
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class TemplateParser:
    """
    Parses user-defined template configurations.
    
    Templates are JSON/YAML files that define how to map canonical model to output format.
    """
    
    def __init__(self):
        """Initialize template parser."""
        pass
    
    def parse_from_file(
        self, 
        template_path: str,
        canonical_sample: Optional[Dict[str, Any]] = None,
        use_ai_mapping: bool = True
    ) -> Dict[str, Any]:
        """
        Parse template from file.
        
        Supports:
        - JSON files (.json): Full template configuration
        - CSV files (.csv): Auto-generate template from CSV headers with AI-powered mapping
        
        Args:
            template_path: Path to template file (JSON or CSV)
            canonical_sample: Optional sample canonical model for AI-powered CSV header mapping
            use_ai_mapping: Whether to use AI for CSV header mapping (default: True)
            
        Returns:
            Template configuration dictionary
        """
        path = Path(template_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        suffix = path.suffix.lower()
        
        if suffix == '.json':
            # Parse JSON template
            with open(path, 'r', encoding='utf-8') as f:
                template = json.load(f)
                return self._validate_template(template)
        
        elif suffix == '.csv':
            # Parse CSV template - read headers and auto-generate template
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            headers = None
            
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding, newline='') as f:
                        reader = csv.reader(f)
                        # Read first row as headers
                        headers = next(reader, None)
                        if headers:
                            break
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except Exception:
                    continue
            
            if not headers:
                raise ValueError("CSV template file is empty or has no headers")
            
            # Clean headers (remove empty strings and whitespace)
            headers = [h.strip() for h in headers if h and h.strip()]
            
            if not headers:
                raise ValueError("CSV template file has no valid headers")
            
            # Auto-generate template from CSV headers (with AI mapping if sample available)
            template = self.parse_from_csv_headers(
                headers,
                canonical_sample=canonical_sample,
                use_ai_mapping=use_ai_mapping
            )
            template["name"] = f"Template from {path.name}"
            return template
        
        else:
            raise ValueError(f"Unsupported template format: {suffix}. Supported formats: .json, .csv")
    
    def parse_from_dict(self, template_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse template from dictionary.
        
        Args:
            template_dict: Template configuration dictionary
            
        Returns:
            Validated template configuration
        """
        return self._validate_template(template_dict)
    
    def parse_from_csv_headers(
        self, 
        csv_headers: List[str],
        canonical_sample: Optional[Dict[str, Any]] = None,
        use_ai_mapping: bool = True
    ) -> Dict[str, Any]:
        """
        Parse template from CSV headers with AI-powered intelligent mapping.
        
        This allows users to upload a CSV template and auto-generate mappings.
        Uses Schema Inferencer for intelligent mapping.
        
        Args:
            csv_headers: List of CSV column headers
            canonical_sample: Optional sample canonical model for AI context
            use_ai_mapping: Whether to use AI for mapping (default: True)
            
        Returns:
            Template configuration with auto-generated mappings
        """
        # Try to use Schema Inferencer if available
        try:
            from src.core.ai.schema_inferencer import SchemaInferencer
            schema_inferencer = SchemaInferencer()
            
            if use_ai_mapping:
                inferred_schema = schema_inferencer.infer_schema(
                    csv_headers,
                    canonical_sample=canonical_sample
                )
                print("✅ Using AI-powered schema inference for template mapping")
                return inferred_schema
        except Exception as e:
            print(f"⚠️  Schema inference failed: {e}. Falling back to basic mapping.")
        
        # No fallback - require AI mapping
        raise ValueError(
            "AI-powered schema inference is required for CSV template parsing. "
            "Please ensure AI provider (OpenAI or Gemini) is configured in .env file. "
            f"Failed to infer schema for headers: {csv_headers}"
        )
    
    def _ai_map_headers_to_paths(
        self,
        csv_headers: List[str],
        canonical_sample: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Use AI to intelligently map CSV headers to canonical model paths.
        
        Args:
            csv_headers: List of CSV column headers
            canonical_sample: Sample canonical model for context
            
        Returns:
            Dict mapping header -> canonical path
        """
        # Get canonical structure reference
        canonical_structure = self._get_canonical_structure()
        
        # Prepare sample data (limit size to avoid token limits)
        sample_str = json.dumps(canonical_sample, indent=2, default=str)
        if len(sample_str) > 3000:
            # Truncate but keep structure
            sample_str = sample_str[:3000] + "\n... (truncated)"
        
        # Build AI prompt
        prompt = self._build_header_mapping_prompt(
            csv_headers,
            canonical_structure,
            sample_str
        )
        
        # Call AI
        response = self._call_ai_for_mapping(prompt)
        
        # Parse response
        mappings = self._parse_ai_mapping_response(response, csv_headers)
        
        return mappings
    
    def _get_canonical_structure(self) -> Dict[str, Any]:
        """Get complete canonical model structure reference for invoice data."""
        return {
            "invoice": {
                "invoice_number": "Invoice number or ID",
                "invoice_date": "Invoice date",
                "due_date": "Due date",
                "order_number": "Order number",
                "po_number": "PO number",
                "payment_terms": "Payment terms",
                "place_of_supply": "Place of supply"
            },
            "seller": {
                "name": "Seller/vendor name",
                "legal_name": "Seller legal name",
                "tax_id": "Seller GSTIN/tax ID",
                "pan": "Seller PAN",
                "address": {
                    "line1": "Address line 1",
                    "line2": "Address line 2",
                    "city": "City",
                    "state": "State",
                    "postal_code": "Postal code",
                    "country": "Country"
                },
                "contact": {
                    "phone": "Phone",
                    "email": "Email",
                    "website": "Website"
                }
            },
            "buyer": {
                "name": "Buyer/customer/party name",
                "legal_name": "Buyer legal name",
                "tax_id": "Buyer GSTIN/tax ID",
                "pan": "Buyer PAN",
                "address": {
                    "line1": "Address line 1",
                    "line2": "Address line 2",
                    "city": "City",
                    "state": "State",
                    "postal_code": "Postal code",
                    "country": "Country"
                },
                "contact": {
                    "phone": "Phone",
                    "email": "Email"
                }
            },
            "line_items": [{
                "line_number": "Line item number",
                "description": "Item/service description",
                "hsn": "HSN/SAC code",
                "quantity": "Quantity",
                "unit": "Unit of measure",
                "unit_price": "Unit price/rate per unit",
                "discount": "Discount amount",
                "taxable_value": "Taxable value for this item",
                "taxes": {
                    "cgst": {"rate": "CGST rate %", "amount": "CGST amount"},
                    "sgst": {"rate": "SGST rate %", "amount": "SGST amount"},
                    "igst": {"rate": "IGST rate %", "amount": "IGST amount"},
                    "cess": {"rate": "CESS rate %", "amount": "CESS amount"}
                },
                "total": "Total for this line item"
            }],
            "totals": {
                "taxable_value": "Total taxable value (sum of all line items)",
                "discount": "Total discount",
                "cgst": {"rate": "CGST rate %", "amount": "Total CGST amount"},
                "sgst": {"rate": "SGST rate %", "amount": "Total SGST amount"},
                "igst": {"rate": "IGST rate %", "amount": "Total IGST amount"},
                "cess": {"rate": "CESS rate %", "amount": "Total CESS amount"},
                "round_off": "Round off amount (adjustment)",
                "total": "Grand total/invoice total amount",
                "currency": "Currency code"
            },
            "metadata": {
                "ledger": "Ledger account name/code",
                "notes": "Additional notes",
                "source": "Extraction source",
                "extraction_date": "When data was extracted"
            }
        }
    
    def _build_header_mapping_prompt(
        self,
        csv_headers: List[str],
        canonical_structure: Dict[str, Any],
        sample_data: str
    ) -> str:
        """Build AI prompt for header mapping."""
        system_prompt = """You are a deterministic invoice-to-CSV mapping engine.

Task: Map CSV column headers to canonical invoice model paths.

This is invoice data extraction. Map each CSV header to the canonical path that contains the same invoice data.

Mapping Process (deterministic):
1. Identify what invoice data the CSV header represents
2. Find the matching field in the canonical structure
3. Use the EXACT field name from canonical structure
4. Determine the data level: invoice, buyer, seller, line_items, totals, or metadata
5. Construct path using correct format for that level

Path Format Rules:
- Invoice fields: invoice.field_name
- Buyer fields: buyer.field_name (or buyer.address.field_name for address parts)
- Seller fields: seller.field_name (or seller.address.field_name for address parts)
- Line item fields: line_items[].field_name
- Total fields: totals.field_name (or totals.tax.field_name for tax fields)
- Metadata fields: metadata.field_name

Field Name Reference (use exact names from canonical structure):
- Invoice number/ID → invoice.invoice_number
- Date → invoice.invoice_date
- Party/Customer/Buyer name → buyer.name
- Seller/Vendor name → seller.name
- GSTIN/Tax ID → buyer.tax_id or seller.tax_id (use sample data to determine)
- Rate/Price → line_items[].unit_price
- Quantity → line_items[].quantity
- Description → line_items[].description
- HSN/SAC → line_items[].hsn
- Taxable Value → totals.taxable_value (for invoice total) or line_items[].taxable_value (for item)
- CGST/SGST/IGST Amount → totals.cgst.amount, totals.sgst.amount, totals.igst.amount
- Total/Invoice Value → totals.total
- Round Off → totals.round_off
- Ledger → metadata.ledger

Return ONLY JSON: {"HEADER": "canonical.path"}"""
        
        user_prompt = f"""CSV Headers to Map (from user's template):
{json.dumps(csv_headers, indent=2)}

Canonical Invoice Model Structure (available fields):
{json.dumps(canonical_structure, indent=2)}

Sample Extracted Invoice Data (for context - use to understand which entity):
{sample_data}

Task: Map each CSV header to the correct canonical invoice model path.

Process for each header:
1. Identify what invoice data the header represents
2. Find the matching field in the canonical structure
3. Use the exact field name from canonical structure
4. Determine if it's invoice-level, buyer-level, seller-level, line-item-level, totals-level, or metadata-level
5. Use appropriate path format based on level

Path Formats:
- Invoice level: invoice.field_name
- Buyer level: buyer.field_name or buyer.address.field_name
- Seller level: seller.field_name or seller.address.field_name
- Line item level: line_items[].field_name
- Totals level: totals.field_name or totals.tax.field_name
- Metadata level: metadata.field_name

Return JSON mapping with exact header names as keys: {{"HEADER": "canonical.path"}}"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    def _call_ai_for_mapping(self, prompt: str) -> str:
        """Call AI API for header mapping (OpenAI primary, Gemini fallback)."""
        # Try OpenAI first
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai_key != 'your_openai_api_key_here' and openai_key.strip():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an expert at mapping CSV headers to invoice data fields. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                if response and response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"⚠️  OpenAI mapping failed: {e}")
        
        # Fallback to Gemini
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key and gemini_key != 'your_gemini_api_key_here' and gemini_key.strip():
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model_name = os.getenv('AI_MODEL', 'gemini-2.5-flash')
                
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 2000,
                    }
                )
                
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"⚠️  Gemini mapping failed: {e}")
        
        raise Exception("No AI provider available for header mapping")
    
    def _parse_ai_mapping_response(self, response: str, csv_headers: List[str]) -> Dict[str, str]:
        """Parse AI response to extract header mappings."""
        # Extract JSON from response
        json_text = self._extract_json_from_response(response)
        
        if not json_text:
            raise ValueError("No JSON found in AI response")
        
        try:
            mappings = json.loads(json_text)
            if not isinstance(mappings, dict):
                raise ValueError("AI response is not a dictionary")
            
            # Validate all headers are mapped
            result = {}
            for header in csv_headers:
                # Try exact match first
                if header in mappings:
                    result[header] = mappings[header]
                else:
                    # Try case-insensitive match
                    found = False
                    for key, value in mappings.items():
                        if key.lower() == header.lower():
                            result[header] = value
                            found = True
                            break
                    if not found:
                        # No fallback - AI must map all headers
                        raise ValueError(
                            f"AI failed to map header '{header}'. "
                            f"Please ensure AI provider is configured and try again."
                        )
            
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {e}")
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from AI response, handling various formats."""
        if not response_text:
            return ""
        
        response_text = response_text.strip()
        
        # Try to find JSON in code blocks
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
                if json_part and (json_part.startswith("{") or json_part.startswith("[")):
                    return json_part
        
        # Try to find JSON object directly
        start_idx = response_text.find("{")
        if start_idx >= 0:
            # Find matching closing brace
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
                            try:
                                json.loads(json_candidate)
                                return json_candidate
                            except json.JSONDecodeError:
                                pass
        
        # If still no JSON, try the whole response
        if response_text.startswith("{"):
            try:
                json.loads(response_text)
                return response_text
            except json.JSONDecodeError:
                pass
        
        return ""
    
    # Removed _auto_detect_transform and _auto_detect_path - now fully AI-driven
    # Transform detection is handled by SchemaInferencer
    # Path detection is handled by AI-powered header mapping
    
    def _validate_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate template structure.
        
        Args:
            template: Template dictionary
            
        Returns:
            Validated template
        """
        # Ensure required fields
        if "columns" not in template:
            raise ValueError("Template must have 'columns' field")
        
        # Validate columns
        for col in template["columns"]:
            if "header" not in col:
                raise ValueError("Each column must have 'header' field")
            if "path" not in col:
                raise ValueError("Each column must have 'path' field")
        
        # Validate repeat rule if present
        if "repeat" in template and template["repeat"]:
            if not isinstance(template["repeat"], str):
                raise ValueError("'repeat' must be a JSONPath string (e.g., 'line_items')")
        
        return template
    
    def create_default_template(self) -> Dict[str, Any]:
        """
        Create a default template for common invoice export.
        
        Returns:
            Default template configuration
        """
        return {
            "name": "Default Invoice Template",
            "columns": [
                {
                    "header": "Invoice No",
                    "path": "invoice.invoice_number"
                },
                {
                    "header": "Invoice Date",
                    "path": "invoice.invoice_date",
                    "transform": "date:DD-MM-YYYY"
                },
                {
                    "header": "Customer Name",
                    "path": "buyer.name"
                },
                {
                    "header": "Taxable Value",
                    "path": "totals.taxable_value",
                    "transform": "number:2"
                },
                {
                    "header": "CGST Amount",
                    "path": "totals.cgst.amount",
                    "transform": "number:2"
                },
                {
                    "header": "SGST Amount",
                    "path": "totals.sgst.amount",
                    "transform": "number:2"
                },
                {
                    "header": "IGST Amount",
                    "path": "totals.igst.amount",
                    "transform": "number:2"
                },
                {
                    "header": "Total",
                    "path": "totals.total",
                    "transform": "number:2"
                }
            ],
            "repeat": None  # One row per invoice
        }
    
    def create_line_items_template(self) -> Dict[str, Any]:
        """
        Create template for line item-level export (GSTR-1 style).
        
        Returns:
            Line items template configuration
        """
        return {
            "name": "Line Items Template",
            "columns": [
                {
                    "header": "Invoice No",
                    "path": "invoice.invoice_number"
                },
                {
                    "header": "Description",
                    "path": "description"
                },
                {
                    "header": "HSN",
                    "path": "hsn"
                },
                {
                    "header": "Quantity",
                    "path": "quantity",
                    "transform": "number:2"
                },
                {
                    "header": "Taxable Value",
                    "path": "taxable_value",
                    "transform": "number:2"
                },
                {
                    "header": "CGST Rate",
                    "path": "taxes.cgst.rate",
                    "transform": "number:2"
                },
                {
                    "header": "CGST Amount",
                    "path": "taxes.cgst.amount",
                    "transform": "number:2"
                },
                {
                    "header": "SGST Rate",
                    "path": "taxes.sgst.rate",
                    "transform": "number:2"
                },
                {
                    "header": "SGST Amount",
                    "path": "taxes.sgst.amount",
                    "transform": "number:2"
                },
                {
                    "header": "IGST Rate",
                    "path": "taxes.igst.rate",
                    "transform": "number:2"
                },
                {
                    "header": "IGST Amount",
                    "path": "taxes.igst.amount",
                    "transform": "number:2"
                }
            ],
            "repeat": "line_items"  # One row per line item
        }
    
    def list_default_templates(self) -> List[str]:
        """
        List available default templates.
        
        Returns:
            List of template names
        """
        return [
            "gstr1",
            "tally",
            "quickbooks",
            "xero",
            "simple_invoice",
            "audit_trail"
        ]
    
    def load_default_template(self, template_name: str) -> Dict[str, Any]:
        """
        Load a default template by name.
        
        Args:
            template_name: Name of the template (e.g., "gstr1", "tally")
            
        Returns:
            Template configuration dictionary
            
        Raises:
            FileNotFoundError: If template not found
        """
        from pathlib import Path
        
        # Get templates directory (should be in project root)
        project_root = Path(__file__).parent.parent.parent.parent
        templates_dir = project_root / "templates"
        
        # Try different case variations
        template_file = None
        for ext in [".json", ".JSON"]:
            for case in [template_name.lower(), template_name.upper(), template_name]:
                candidate = templates_dir / f"{case}{ext}"
                if candidate.exists():
                    template_file = candidate
                    break
            if template_file:
                break
        
        if not template_file:
            available = ", ".join(self.list_default_templates())
            raise FileNotFoundError(
                f"Template '{template_name}' not found. "
                f"Available templates: {available}"
            )
        
        return self.parse_from_file(str(template_file))
