"""
Dynamic Mapper - AI-powered mapping between canonical data and template columns.
No hardcoded mappings - pure semantic understanding.
"""
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .ai_client import AIClient
from .context_analyzer import ContextAnalyzer
from .prompt_generator import PromptGenerator


class DynamicMapper:
    """
    Maps extracted invoice data to template columns using AI.
    Handles missing fields, transformations, and array-to-single-value conversions.
    Uses dynamic prompt generation based on context.
    """
    
    def __init__(self, ai_client: Optional[AIClient] = None, use_dynamic_prompts: bool = True):
        """
        Initialize dynamic mapper.
        
        Args:
            ai_client: Optional AI client (creates new one if not provided)
            use_dynamic_prompts: Whether to use dynamic prompt generation (default: True)
        """
        self.ai_client = ai_client or AIClient()
        self.use_dynamic_prompts = use_dynamic_prompts
        
        if use_dynamic_prompts:
            self.context_analyzer = ContextAnalyzer(ai_client)
            self.prompt_generator = PromptGenerator(ai_client)
            print("📝 [DYNAMIC MAPPER] Using dynamic prompt generation")
        else:
            self._load_mapping_prompt()
            print("📝 [DYNAMIC MAPPER] Using static prompts")
    
    def _load_mapping_prompt(self):
        """Load mapping prompt template (fallback)."""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "mapping_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        else:
            self.prompt_template = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default mapping prompt."""
        return """You are an expert at mapping invoice data to template columns.

Your task: Map canonical invoice data to template columns semantically.

Key Principles:
1. Understand semantic meaning - match data to columns based on what they represent
2. Handle missing data intelligently - suggest alternatives or leave empty
3. Transform data types/formats as needed (dates, numbers, text)
4. Handle arrays → single values (e.g., line_items[].unit_price → first item or aggregate)
5. Preserve data accuracy - don't modify values, only transform format

Return mapped values for each template column."""
    
    def map_to_template(
        self,
        canonical_data: Dict[str, Any],
        template_schema: Dict[str, Any],
        mapping_history: Optional[List[Dict]] = None,
        document_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Map canonical invoice data to template columns.
        
        Args:
            canonical_data: Extracted invoice data (canonical model)
            template_schema: Template schema with column definitions
            mapping_history: Optional previous mappings for learning
            document_text: Optional document text for context analysis
        
        Returns:
            Mapped data ready for export: {column_name: value}
        """
        print("🗺️  [DYNAMIC MAPPER] Starting mapping...")
        print(f"🗺️  [DYNAMIC MAPPER] Canonical data keys: {list(canonical_data.keys())}")

        # Quick canonical summary to detect empty/invalid extraction early
        invoice_number = canonical_data.get('invoice', {}).get('invoice_number')
        invoice_date = canonical_data.get('invoice', {}).get('invoice_date')
        buyer_name = canonical_data.get('buyer', {}).get('name')
        totals_total = canonical_data.get('totals', {}).get('total')
        line_items = canonical_data.get('line_items', [])

        print(f"🗺️  [DYNAMIC MAPPER] Canonical summary -> invoice_number: {invoice_number}, invoice_date: {invoice_date}, buyer: {buyer_name}, total: {totals_total}, line_items: {len(line_items)}")

        # Fail fast if canonical is effectively empty
        if not invoice_number and not buyer_name and totals_total in (None, "") and len(line_items) == 0:
            raise ValueError("Canonical data is empty (no invoice_number, buyer, totals, or line_items). Aborting mapping to avoid blank CSV.")
        
        # Check if canonical has any data
        has_data = False
        if canonical_data.get('invoice', {}).get('invoice_number'):
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has invoice_number: {canonical_data['invoice']['invoice_number']}")
            has_data = True
        if canonical_data.get('buyer', {}).get('name'):
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has buyer name: {canonical_data['buyer']['name']}")
            has_data = True
        if canonical_data.get('totals', {}).get('total'):
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has total: {canonical_data['totals']['total']}")
            has_data = True
        
        # Check for missing fields that are commonly not mapped
        totals = canonical_data.get('totals', {})
        if totals.get('sgst', {}).get('amount') is not None:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has SGST: {totals['sgst']['amount']}")
        else:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical SGST: {totals.get('sgst', 'missing')}")
        
        if totals.get('total') is not None:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has INVOICE VALUE (total): {totals['total']}")
        else:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical INVOICE VALUE (total): missing")
        
        if totals.get('round_off') is not None:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has ROUND OFF: {totals['round_off']}")
        else:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical ROUND OFF: missing")
        
        metadata = canonical_data.get('metadata', {})
        if metadata.get('ledger'):
            print(f"🗺️  [DYNAMIC MAPPER] Canonical has LEDGER: {metadata['ledger']}")
        else:
            print(f"🗺️  [DYNAMIC MAPPER] Canonical LEDGER: missing")
        
        if not has_data:
            print("⚠️  [DYNAMIC MAPPER] WARNING: Canonical data appears to be empty!")
        
        columns = template_schema.get('columns', [])
        print(f"🗺️  [DYNAMIC MAPPER] Template has {len(columns)} columns: {[col.get('header') for col in columns]}")
        
        # Generate dynamic prompt if enabled
        if self.use_dynamic_prompts:
            print("🌍 [DYNAMIC MAPPER] Analyzing context...")
            context = self.context_analyzer.analyze_context(
                canonical_data, template_schema, document_text
            )
            
            # Discover relationships
            discovered_relationships = self._analyze_data_relationships(
                canonical_data, template_schema
            )
            
            print("📝 [DYNAMIC MAPPER] Generating context-aware prompt...")
            system_prompt = self.prompt_generator.generate_mapping_prompt(
                context, template_schema, discovered_relationships
            )
        else:
            # Use static prompt
            system_prompt = self.prompt_template
        
        # Build user prompt
        user_prompt = self._build_mapping_prompt(
            canonical_data, template_schema, mapping_history
        )
        print(f"🗺️  [DYNAMIC MAPPER] Built prompt: {len(user_prompt)} chars")
        
        # Call AI with retry logic (2-3 attempts)
        max_retries = 3
        last_error = None
        last_mapped_data = None
        
        for attempt in range(1, max_retries + 1):
            print(f"🗺️  [DYNAMIC MAPPER] Calling AI (attempt {attempt}/{max_retries})...")
            
            try:
                # Adjust temperature slightly on retries for variation
                temperature = 0.1 if attempt == 1 else 0.2
                
                response = self.ai_client.call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )
                
                print(f"🗺️  [DYNAMIC MAPPER] AI response received: {len(response)} chars")
                print(f"🗺️  [DYNAMIC MAPPER] AI response preview: {response[:500]}...")
                
                # Parse JSON response
                mapped_data = self.ai_client.extract_json(response)
                print(f"🗺️  [DYNAMIC MAPPER] Parsed mapped data: {len(mapped_data)} columns")
                print(f"🗺️  [DYNAMIC MAPPER] Mapped data keys: {list(mapped_data.keys())}")
                
                # Show mapped values
                for key, value in mapped_data.items():
                    if value:
                        print(f"🗺️  [DYNAMIC MAPPER] {key} = {value}")
                
                # Validate all columns are mapped
                validated = self._validate_mapping(mapped_data, template_schema)
                
                # Check for quality issues (duplicate values, calculation errors)
                quality_issues = self._check_mapping_quality(validated, canonical_data, template_schema)
                
                if not quality_issues:
                    # Good mapping, return it
                    print(f"🗺️  [DYNAMIC MAPPER] Validated mapping: {len(validated)} columns")
                    print("✅ [DYNAMIC MAPPER] Mapping complete (quality check passed)")
                    return validated
                else:
                    # Quality issues detected, retry with feedback
                    print(f"⚠️  [DYNAMIC MAPPER] Quality issues detected: {quality_issues}")
                    if attempt < max_retries:
                        print(f"🔄 [DYNAMIC MAPPER] Retrying with improved prompt...")
                        # Regenerate prompt with feedback if using dynamic prompts
                        if self.use_dynamic_prompts:
                            # Re-analyze context and regenerate prompt
                            context = self.context_analyzer.analyze_context(
                                canonical_data, template_schema, document_text
                            )
                            discovered_relationships = self._analyze_data_relationships(
                                canonical_data, template_schema
                            )
                            system_prompt = self.prompt_generator.generate_mapping_prompt(
                                context, template_schema, discovered_relationships
                            )
                        
                        # Enhance user prompt with feedback
                        user_prompt = self._build_retry_prompt(
                            canonical_data, template_schema, validated, quality_issues, mapping_history
                        )
                        last_mapped_data = validated
                        continue
                    else:
                        # Last attempt, use the best we have
                        print(f"⚠️  [DYNAMIC MAPPER] Using mapping despite quality issues (max retries reached)")
                        print(f"🗺️  [DYNAMIC MAPPER] Validated mapping: {len(validated)} columns")
                        print("✅ [DYNAMIC MAPPER] Mapping complete (with warnings)")
                        return validated
                
            except Exception as e:
                last_error = e
                print(f"❌ [DYNAMIC MAPPER] Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    print(f"🔄 [DYNAMIC MAPPER] Retrying...")
                    continue
                else:
                    # Last attempt failed, use last_mapped_data if available
                    if last_mapped_data:
                        print(f"⚠️  [DYNAMIC MAPPER] Using previous mapping (best effort)")
                        return last_mapped_data
                    # No fallback, raise error
                    import traceback
                    print(f"❌ [DYNAMIC MAPPER] Traceback: {traceback.format_exc()}")
                    raise Exception(f"Dynamic mapping failed after {max_retries} attempts: {str(e)}") from e
        
        # Should not reach here, but return last_mapped_data if available
        if last_mapped_data:
            return last_mapped_data
        raise Exception(f"Dynamic mapping failed: {last_error}") from last_error
    
    def _build_mapping_prompt(
        self,
        canonical_data: Dict[str, Any],
        template_schema: Dict[str, Any],
        mapping_history: Optional[List[Dict]]
    ) -> str:
        """Build mapping prompt from data and schema."""
        columns = template_schema.get('columns', [])
        column_names = [col.get('header', '') for col in columns]
        
        # Discover relationships from data
        discovered_relationships = self._analyze_data_relationships(canonical_data, template_schema)
        
        # Build a summary of where to find common fields
        field_guide = """
IMPORTANT FIELD MAPPINGS:
- DATE / INVOICE DATE → invoice.invoice_date
- PARTY NAME / BUYER NAME → buyer.name
- INVOICE NO / INVOICE NUMBER → invoice.invoice_number
- GSTIN / TAX ID → buyer.tax_id
- RATE → line_items[].unit_price (analyze line_items to understand relationship with TAXABLE VALUE)
- TAXABLE VALUE → totals.taxable_value OR discover from line_items
- CGST → totals.cgst.amount (or discover calculation if rate is available)
- SGST → totals.sgst.amount (or discover calculation if rate is available)
- IGST → totals.igst.amount
- INVOICE VALUE / TOTAL → totals.total (or discover calculation from components)
- ROUND OFF → totals.round_off (may be null/0)
- LEDGER → metadata.ledger (may be null)
"""
        
        # Get full canonical data (don't truncate too much)
        canonical_json = json.dumps(canonical_data, indent=2, default=str)
        
        # Build explicit column list for AI
        column_list = [col.get('header', '') for col in columns]
        
        prompt = f"""You MUST map ALL {len(columns)} template columns to invoice data. Return a value for EVERY column.

{discovered_relationships}

REQUIRED COLUMNS (you must return ALL of these - EXACTLY {len(columns)} keys):
{json.dumps(column_list, indent=2)}

Template Column Definitions:
{json.dumps(columns, indent=2)[:3000]}

{field_guide}

Invoice Data (Canonical Model):
{canonical_json[:5000]}

CRITICAL REQUIREMENTS:
1. You MUST return a value for EVERY column listed above - NO EXCEPTIONS
2. Your response must be a JSON object with EXACTLY {len(columns)} keys matching the REQUIRED COLUMNS list
3. DO NOT copy the same value to multiple columns - each column must have its own unique value
4. EXCEPTION: CGST and SGST CAN be equal (intra-state transactions split tax equally)
5. NEVER INVENT OR HALLUCINATE VALUES. Only use values present in the canonical data or derived from discovered relationships. If a value is missing, return null.
6. Do NOT create fake parties, invoice numbers, dates, GSTINs, or amounts. Use the exact values from canonical; otherwise null.
7. Use the discovered relationships above to understand calculations and patterns
8. If a calculation pattern is discovered, use it when explicit values are missing
9. If percentages are involved (tax rates), understand that amounts may be calculated
10. Extract values directly from canonical model when available
11. For SGST: Check totals.sgst.amount (it may be 0.0 or a number, but it exists in the structure)
12. For INVOICE VALUE: Use totals.total (the final invoice total amount)
13. For ROUND OFF: Check totals.round_off (may be null/0 if not applicable)
14. For LEDGER: Check metadata.ledger (may be null if not present)
15. If a field is truly missing, use null (not empty string)
16. Use the EXACT column names from the REQUIRED COLUMNS list above

Return JSON with EXACTLY these {len(columns)} keys (copy the exact names):
{{
"""
        # List ALL columns explicitly
        for col in columns:
            header = col.get('header', '')
            prompt += f'  "{header}": "value_or_null",\n'
        prompt += "}"
        
        if mapping_history:
            prompt += f"""

Previous Mappings (for reference):
{json.dumps(mapping_history[-3:], indent=2)[:1000]}
"""
        
        return prompt
    
    def _validate_mapping(
        self,
        mapped_data: Dict[str, Any],
        template_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that all columns are mapped."""
        columns = template_schema.get('columns', [])
        column_names = {col.get('header') for col in columns}
        mapped_names = set(mapped_data.keys())
        
        # Check for missing columns
        missing = column_names - mapped_names
        if missing:
            print(f"⚠️  [DYNAMIC MAPPER] AI did not return these columns: {missing}")
            print(f"⚠️  [DYNAMIC MAPPER] This should not happen - AI was instructed to return ALL columns")
        
        # Ensure all columns have values (even if null)
        for col in columns:
            header = col.get('header')
            if header and header not in mapped_data:
                print(f"⚠️  [DYNAMIC MAPPER] Adding missing column '{header}' as None")
                mapped_data[header] = None
        
        return mapped_data
    
    def _analyze_data_relationships(
        self,
        canonical_data: Dict[str, Any],
        template_schema: Dict[str, Any]
    ) -> str:
        """
        Analyze canonical data to discover relationships, calculations, and patterns.
        Returns a description of discovered relationships for the AI prompt.
        """
        analysis = []
        line_items = canonical_data.get('line_items', [])
        totals = canonical_data.get('totals', {})
        invoice = canonical_data.get('invoice', {})
        buyer = canonical_data.get('buyer', {})
        metadata = canonical_data.get('metadata', {})
        
        def _is_missing(val):
            return val is None or val == "" or val == [] or val == {}
        
        # Discover tax rate patterns
        if line_items:
            first_item = line_items[0]
            item_taxable = first_item.get('taxable_value')
            item_cgst = first_item.get('taxes', {}).get('cgst', {})
            item_sgst = first_item.get('taxes', {}).get('sgst', {})
            
            cgst_rate = item_cgst.get('rate')
            cgst_amount = item_cgst.get('amount')
            sgst_rate = item_sgst.get('rate')
            sgst_amount = item_sgst.get('amount')
            
            if item_taxable and cgst_rate and cgst_amount:
                # Discover: CGST amount = taxable * (rate / 100)?
                try:
                    calculated = item_taxable * (cgst_rate / 100)
                    if abs(calculated - cgst_amount) < 0.01:
                        analysis.append(f"DISCOVERED: CGST amount appears to be calculated as taxable_value * (CGST_rate / 100). Example: {item_taxable} * ({cgst_rate}/100) = {cgst_amount}")
                except (TypeError, ValueError):
                    pass
            
            if item_taxable and sgst_rate and sgst_amount:
                try:
                    calculated = item_taxable * (sgst_rate / 100)
                    if abs(calculated - sgst_amount) < 0.01:
                        analysis.append(f"DISCOVERED: SGST amount appears to be calculated as taxable_value * (SGST_rate / 100). Example: {item_taxable} * ({sgst_rate}/100) = {sgst_amount}")
                except (TypeError, ValueError):
                    pass
            
            # Discover RATE vs TAXABLE VALUE relationship
            unit_price = first_item.get('unit_price')
            quantity = first_item.get('quantity', 1)
            if unit_price and item_taxable:
                try:
                    if abs(unit_price * quantity - item_taxable) < 0.01:
                        analysis.append(f"DISCOVERED: TAXABLE VALUE = unit_price * quantity. Example: {unit_price} * {quantity} = {item_taxable}")
                    elif quantity == 1 and abs(unit_price - item_taxable) < 0.01:
                        analysis.append(f"DISCOVERED: When quantity=1, TAXABLE VALUE equals unit_price. Both are {item_taxable}")
                except (TypeError, ValueError):
                    pass
        
        # Discover total calculation patterns
        totals_taxable = totals.get('taxable_value')
        totals_cgst = totals.get('cgst', {}).get('amount')
        totals_sgst = totals.get('sgst', {}).get('amount')
        totals_igst = totals.get('igst', {}).get('amount')
        totals_total = totals.get('total')
        
        if totals_taxable and totals_cgst and totals_sgst and totals_total:
            try:
                expected = totals_taxable + totals_cgst + totals_sgst
                if abs(expected - totals_total) < 0.01:
                    analysis.append(f"DISCOVERED: INVOICE VALUE = TAXABLE VALUE + CGST + SGST. Example: {totals_taxable} + {totals_cgst} + {totals_sgst} = {totals_total}")
                else:
                    round_off = totals.get('round_off')
                    if round_off:
                        expected_with_round = expected + round_off
                        if abs(expected_with_round - totals_total) < 0.01:
                            analysis.append(f"DISCOVERED: INVOICE VALUE = TAXABLE VALUE + CGST + SGST + ROUND OFF. Example: {totals_taxable} + {totals_cgst} + {totals_sgst} + {round_off} = {totals_total}")
            except (TypeError, ValueError):
                pass
        
        # Discover percentage patterns
        if totals_taxable and totals_cgst:
            try:
                potential_rate = (totals_cgst / totals_taxable) * 100 if totals_taxable > 0 else None
                if potential_rate and potential_rate > 0 and potential_rate < 100:
                    # Check if this matches a known tax rate
                    known_rates = [5, 9, 12, 18, 28]
                    closest = min(known_rates, key=lambda x: abs(x - potential_rate))
                    if abs(closest - potential_rate) < 0.5:
                        analysis.append(f"DISCOVERED: CGST appears to be {closest}% of TAXABLE VALUE. CGST amount = TAXABLE VALUE * ({closest}/100)")
            except (TypeError, ValueError, ZeroDivisionError):
                pass
        
        if totals_taxable and totals_sgst:
            try:
                potential_rate = (totals_sgst / totals_taxable) * 100 if totals_taxable > 0 else None
                if potential_rate and potential_rate > 0 and potential_rate < 100:
                    known_rates = [5, 9, 12, 18, 28]
                    closest = min(known_rates, key=lambda x: abs(x - potential_rate))
                    if abs(closest - potential_rate) < 0.5:
                        analysis.append(f"DISCOVERED: SGST appears to be {closest}% of TAXABLE VALUE. SGST amount = TAXABLE VALUE * ({closest}/100)")
            except (TypeError, ValueError, ZeroDivisionError):
                pass
        
        if analysis:
            return "DATA RELATIONSHIPS DISCOVERED FROM THIS INVOICE:\n" + "\n".join(f"- {a}" for a in analysis)
        else:
            return "No clear calculation patterns discovered. Extract values directly from canonical model."
    
    def _check_mapping_quality(
        self,
        mapped_data: Dict[str, Any],
        canonical_data: Dict[str, Any],
        template_schema: Dict[str, Any]
    ) -> List[str]:
        """
        Check mapping quality - detect duplicate values, calculation errors, etc.
        Returns list of quality issues found.
        """
        issues = []
        line_items = canonical_data.get('line_items', [])
        totals = canonical_data.get('totals', {})
        invoice = canonical_data.get('invoice', {})
        buyer = canonical_data.get('buyer', {})
        metadata = canonical_data.get('metadata', {})
        
        def _is_missing(val):
            return val is None or val == "" or val == [] or val == {}

        # If almost everything is null, flag as a quality issue
        non_null = [v for v in mapped_data.values() if not _is_missing(v)]
        null_ratio = 1.0 - (len(non_null) / max(len(mapped_data), 1))
        key_fields = [
            mapped_data.get('DATE'),
            mapped_data.get('PARTY NAME'),
            mapped_data.get('INVOICE NO'),
            mapped_data.get('GSTIN'),
            mapped_data.get('TAXABLE VALUE'),
            mapped_data.get('INVOICE VALUE')
        ]
        if null_ratio > 0.7 or all(_is_missing(k) for k in key_fields):
            issues.append("All (or most) mapped values are null. Canonical data may be empty; do not accept this mapping.")
        
        # Check for duplicate non-null values in different columns
        value_to_columns = {}
        for col_name, value in mapped_data.items():
            if value is not None and value != "":
                normalized = str(value).strip()
                if normalized in value_to_columns:
                    value_to_columns[normalized].append(col_name)
                else:
                    value_to_columns[normalized] = [col_name]
        
        # Find duplicates (same value in multiple columns)
        for value, columns in value_to_columns.items():
            if len(columns) > 1:
                col_upper = [c.upper() for c in columns]
                
                # LEGITIMATE cases where same values are OK:
                # 1. CGST and SGST can be equal (intra-state transactions split tax equally)
                if 'CGST' in col_upper and 'SGST' in col_upper and len(columns) == 2:
                    # This is OK - CGST and SGST are often equal
                    continue
                
                # 2. Check if RATE = TAXABLE VALUE is legitimate
                if 'RATE' in col_upper and 'TAXABLE VALUE' in col_upper:
                    # Check canonical to see if quantity = 1 or if they're actually different
                    if line_items:
                        first_item = line_items[0]
                        quantity = first_item.get('quantity', 1)
                        unit_price = first_item.get('unit_price')
                        taxable_value = first_item.get('taxable_value')
                        
                        # If quantity = 1, RATE = TAXABLE VALUE is OK
                        if quantity == 1 and unit_price and taxable_value:
                            try:
                                if abs(float(unit_price) - float(taxable_value)) < 0.01:
                                    continue  # This is OK
                            except (TypeError, ValueError):
                                pass
                        # If they're different in canonical, flag it
                        elif unit_price and taxable_value:
                            try:
                                if abs(float(unit_price) - float(taxable_value)) > 0.01:
                                    issues.append(f"RATE ({unit_price}) and TAXABLE VALUE ({taxable_value}) are different in invoice but mapped to same value '{value}'. Check line_items for correct values.")
                            except (TypeError, ValueError):
                                pass
                    else:
                        issues.append(f"Same value '{value}' in RATE and TAXABLE VALUE columns. Check canonical data to discover if they should be different.")
                
                # Other numeric columns should be different
                numeric_cols = ['RATE', 'TAXABLE VALUE', 'CGST', 'SGST', 'IGST', 'INVOICE VALUE', 'ROUND OFF']
                if any(col.upper() in numeric_cols for col in columns):
                    # Check if these are tax components that might legitimately be same
                    if not ('CGST' in col_upper and 'SGST' in col_upper):
                        issues.append(f"Same value '{value}' found in multiple columns: {columns}. Analyze canonical data to discover if these should have different values or if a calculation is needed.")
        
        # Hallucination checks: if canonical is missing a value but mapping has a non-null value, flag it
        # INVOICE NO
        if _is_missing(invoice.get('invoice_number')) and mapped_data.get('INVOICE NO'):
            issues.append("INVOICE NO not present in canonical data, but mapping provided a value. Use null if missing.")
        # PARTY NAME
        if _is_missing(buyer.get('name')) and mapped_data.get('PARTY NAME'):
            issues.append("PARTY NAME not present in canonical data, but mapping provided a value. Use null if missing.")
        # GSTIN / TAX ID
        if _is_missing(buyer.get('tax_id')) and mapped_data.get('GSTIN'):
            issues.append("GSTIN not present in canonical data, but mapping provided a value. Use null if missing.")
        # INVOICE VALUE / total
        if _is_missing(totals.get('total')) and mapped_data.get('INVOICE VALUE'):
            issues.append("INVOICE VALUE not present in canonical totals, but mapping provided a value. Use null if missing.")
        # RATE
        line_unit_price = None
        if line_items:
            first_item = line_items[0]
            line_unit_price = first_item.get('unit_price')
        if _is_missing(line_unit_price) and mapped_data.get('RATE'):
            issues.append("RATE (unit price or rate) not present in canonical line items, but mapping provided a value. Use null if missing.")
        # TAXABLE VALUE
        if _is_missing(totals.get('taxable_value')) and mapped_data.get('TAXABLE VALUE'):
            issues.append("TAXABLE VALUE not present in canonical totals, but mapping provided a value. Use null if missing.")
        # CGST / SGST
        if _is_missing(totals.get('cgst', {}).get('amount')) and mapped_data.get('CGST'):
            issues.append("CGST not present in canonical totals, but mapping provided a value. Use null if missing.")
        if _is_missing(totals.get('sgst', {}).get('amount')) and mapped_data.get('SGST'):
            issues.append("SGST not present in canonical totals, but mapping provided a value. Use null if missing.")
        # LEDGER
        if _is_missing(metadata.get('ledger')) and mapped_data.get('LEDGER'):
            issues.append("LEDGER not present in canonical metadata, but mapping provided a value. Use null if missing.")
        
        # Check if calculations should be discovered
        taxable_value = mapped_data.get('TAXABLE VALUE')
        cgst = mapped_data.get('CGST')
        sgst = mapped_data.get('SGST')
        invoice_value = mapped_data.get('INVOICE VALUE')
        rate = mapped_data.get('RATE')
        
        # Check tax rate calculations
        try:
            if totals:
                cgst_rate = totals.get('cgst', {}).get('rate')
                sgst_rate = totals.get('sgst', {}).get('rate')
                
                if cgst_rate and taxable_value and cgst:
                    taxable = float(str(taxable_value).replace(',', ''))
                    cgst_val = float(str(cgst).replace(',', ''))
                    expected_cgst_rate = (cgst_val / taxable) * 100 if taxable > 0 else None
                    
                    if expected_cgst_rate and cgst_rate:
                        if abs(expected_cgst_rate - cgst_rate) > 0.1:
                            issues.append(f"CGST amount ({cgst_val}) doesn't match expected rate. Taxable Value ({taxable}) * {cgst_rate}% should be {taxable * cgst_rate / 100}, but got {cgst_val}.")
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        
        # Check RATE vs TAXABLE VALUE relationship
        try:
            if rate and taxable_value and line_items:
                rate_val = float(str(rate).replace(',', ''))
                taxable = float(str(taxable_value).replace(',', ''))
                
                first_item = line_items[0]
                unit_price = first_item.get('unit_price')
                quantity = first_item.get('quantity', 1)
                item_taxable = first_item.get('taxable_value')
                
                # RATE should typically be unit_price
                if unit_price:
                    unit_price_val = float(str(unit_price).replace(',', ''))
                    if abs(rate_val - unit_price_val) > 0.01:
                        issues.append(f"RATE ({rate_val}) doesn't match unit_price from line_items ({unit_price_val}). RATE should be the unit price.")
                
                # TAXABLE VALUE might be unit_price * quantity (or sum of line items)
                if item_taxable:
                    item_taxable_val = float(str(item_taxable).replace(',', ''))
                    if abs(taxable - item_taxable_val) > 0.01:
                        # Check if it's sum of all line items
                        total_taxable = sum(float(str(item.get('taxable_value', 0)).replace(',', '')) for item in line_items)
                        if abs(taxable - total_taxable) > 0.01:
                            issues.append(f"TAXABLE VALUE ({taxable}) doesn't match line items. Expected: {total_taxable} (sum of line items).")
        except (ValueError, TypeError):
            pass
        
        # Check INVOICE VALUE calculation
        try:
            if taxable_value and cgst and sgst and invoice_value:
                taxable = float(str(taxable_value).replace(',', ''))
                cgst_val = float(str(cgst).replace(',', ''))
                sgst_val = float(str(sgst).replace(',', ''))
                invoice = float(str(invoice_value).replace(',', ''))
                
                expected_total = taxable + cgst_val + sgst_val
                if abs(invoice - expected_total) > 0.01:
                    round_off = mapped_data.get('ROUND OFF')
                    if round_off:
                        try:
                            round_val = float(str(round_off).replace(',', ''))
                            expected_with_round = expected_total + round_val
                            if abs(invoice - expected_with_round) > 0.01:
                                issues.append(f"INVOICE VALUE ({invoice}) doesn't match: TAXABLE VALUE ({taxable}) + CGST ({cgst_val}) + SGST ({sgst_val}) + ROUND OFF ({round_off}) = {expected_with_round}")
                        except:
                            pass
                    else:
                        issues.append(f"INVOICE VALUE ({invoice}) doesn't match: TAXABLE VALUE ({taxable}) + CGST ({cgst_val}) + SGST ({sgst_val}) = {expected_total}")
        except (ValueError, TypeError):
            pass
        
        return issues
    
    def _build_retry_prompt(
        self,
        canonical_data: Dict[str, Any],
        template_schema: Dict[str, Any],
        previous_mapping: Dict[str, Any],
        quality_issues: List[str],
        mapping_history: Optional[List[Dict]]
    ) -> str:
        """Build retry prompt with feedback about quality issues."""
        columns = template_schema.get('columns', [])
        column_list = [col.get('header', '') for col in columns]
        
        canonical_json = json.dumps(canonical_data, indent=2, default=str)
        
        # Discover relationships again for retry
        discovered_relationships = self._analyze_data_relationships(canonical_data, template_schema)
        
        # Extract calculation context from canonical
        line_items = canonical_data.get('line_items', [])
        totals = canonical_data.get('totals', {})
        
        calculation_examples = ""
        if line_items:
            first_item = line_items[0]
            unit_price = first_item.get('unit_price')
            quantity = first_item.get('quantity', 1)
            item_taxable = first_item.get('taxable_value')
            
            if unit_price is not None and quantity is not None and item_taxable is not None:
                calculation_examples = f"""
CALCULATION EXAMPLES FROM THIS INVOICE:
- First line item: unit_price={unit_price}, quantity={quantity}, taxable_value={item_taxable}
- If quantity=1, RATE (unit_price) might equal TAXABLE VALUE
- If quantity>1, RATE should be unit_price, TAXABLE VALUE should be unit_price * quantity
"""
        
        if totals:
            cgst_rate = totals.get('cgst', {}).get('rate')
            sgst_rate = totals.get('sgst', {}).get('rate')
            taxable = totals.get('taxable_value')
            cgst_amt = totals.get('cgst', {}).get('amount')
            sgst_amt = totals.get('sgst', {}).get('amount')
            
            if cgst_rate and taxable:
                try:
                    expected_cgst = taxable * (cgst_rate / 100)
                    calculation_examples += f"""
- Tax rates: CGST={cgst_rate}%, SGST={sgst_rate}% (if available)
- Tax amounts: CGST={cgst_amt}, SGST={sgst_amt} (from totals)
- If CGST rate is {cgst_rate}% and taxable_value is {taxable}, CGST amount = {taxable} * ({cgst_rate}/100) = {expected_cgst}
"""
                except (TypeError, ValueError):
                    pass
        
        prompt = f"""RETRY REQUEST - Previous mapping had quality issues. Please fix them.

QUALITY ISSUES DETECTED:
{chr(10).join(f"- {issue}" for issue in quality_issues)}

{discovered_relationships}

{calculation_examples}

PREVIOUS MAPPING (for reference - DO NOT COPY VALUES):
{json.dumps(previous_mapping, indent=2)[:2000]}

REQUIRED COLUMNS (you must return ALL of these - EXACTLY {len(columns)} keys):
{json.dumps(column_list, indent=2)}

Template Column Definitions:
{json.dumps(columns, indent=2)[:3000]}

Invoice Data (Canonical Model):
{canonical_json[:5000]}

CRITICAL INSTRUCTIONS:
1. DO NOT copy the same value to multiple columns - each column should have its own unique value
2. EXCEPTION: CGST and SGST CAN be equal (intra-state transactions split tax equally)
3. NEVER INVENT OR HALLUCINATE VALUES. Only use values present in canonical data or derived from discovered relationships. If missing, return null.
4. Do NOT fabricate parties, invoice numbers, dates, GSTINs, or amounts.
5. Use the discovered relationships above to understand calculations and patterns
6. Understand field relationships and calculations:
   - INVOICE VALUE = TAXABLE VALUE + CGST + SGST + IGST + ROUND OFF (if applicable)
   - RATE is typically the unit_price from line_items (first item)
   - TAXABLE VALUE is the base amount before taxes (totals.taxable_value or sum of line items)
   - CGST and SGST are separate tax amounts (may be equal, but are different fields)
   - Tax amounts can be calculated: taxable_value * (rate / 100)
   - ROUND OFF is a small adjustment (usually ±0.01 to ±0.99)
7. Extract values from the canonical model - don't copy from previous mapping
8. Check line_items for RATE (unit_price) and verify TAXABLE VALUE matches
9. If a field is truly missing, use null (not empty string)
10. Use the EXACT column names from the REQUIRED COLUMNS list

Return JSON with EXACTLY these {len(columns)} keys:
{{
"""
        for col in columns:
            header = col.get('header', '')
            prompt += f'  "{header}": "value_or_null",\n'
        prompt += "}"
        
        return prompt
    
    def suggest_mappings(
        self,
        template_columns: List[str],
        available_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Suggest mappings between columns and data paths.
        Used for user confirmation or auto-mapping.
        
        Args:
            template_columns: List of column names
            available_data: Available canonical data
        
        Returns:
            Dict mapping column_name -> suggested_canonical_path
        """
        # Build simplified prompt for suggestions
        prompt = f"""Suggest canonical paths for these template columns:

Columns: {json.dumps(template_columns, indent=2)}

Available Data Structure:
{json.dumps(self._get_data_structure(available_data), indent=2)[:2000]}

Return JSON mapping:
{{
  "Column Name": "suggested.canonical.path",
  ...
}}"""
        
        try:
            response = self.ai_client.call(
                system_prompt="Suggest canonical paths for template columns based on semantic meaning.",
                user_prompt=prompt,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            return self.ai_client.extract_json(response)
        except Exception:
            # Fallback to simple inference
            return {col: f"unknown.{col.lower().replace(' ', '_')}" for col in template_columns}
    
    def _get_data_structure(self, data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
        """Get simplified data structure for AI context."""
        if max_depth == 0:
            return "..."
        
        structure = {}
        for key, value in data.items():
            if isinstance(value, dict):
                structure[key] = self._get_data_structure(value, max_depth - 1)
            elif isinstance(value, list) and value:
                structure[key] = f"[{len(value)} items]"
                if isinstance(value[0], dict):
                    structure[key] = [self._get_data_structure(value[0], max_depth - 1)]
            else:
                structure[key] = type(value).__name__
        
        return structure
