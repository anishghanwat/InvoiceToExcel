"""
Intelligent CSV mapper that matches extracted data to user-defined columns.
"""
import re
import csv
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher

# Try to import AI mapper (optional)
try:
    from .ai_mapper import AIMapper
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    AIMapper = None


class CSVMapper:
    """Maps extracted document data to CSV columns based on user input."""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize the CSV mapper.
        
        Args:
            use_ai: Whether to use AI-powered mapping if available
        """
        self.column_mappings = {}
        self.extracted_data = {}
        self.use_ai = use_ai and AI_AVAILABLE
        
        # Initialize AI mapper if available and enabled
        if self.use_ai:
            provider = os.getenv('AI_PROVIDER', 'gemini').lower()  # Default to Gemini
            model = os.getenv('AI_MODEL')
            try:
                self.ai_mapper = AIMapper(provider=provider, model=model)
                if self.ai_mapper.provider != "none":
                    print(f"✅ AI mapping enabled using {provider} ({self.ai_mapper.model})")
                else:
                    self.use_ai = False
            except Exception as e:
                print(f"⚠️  AI mapper initialization failed: {e}. Using rule-based mapping.")
                self.use_ai = False
        else:
            self.ai_mapper = None
        
    def get_user_columns(self) -> List[str]:
        """
        Get column names from user input.
        
        Returns:
            List of column names
        """
        print("\n" + "="*60)
        print("CSV COLUMN CONFIGURATION")
        print("="*60)
        print("Enter the column names you want in your CSV file.")
        print("Examples: sr.no, particulars, qty, rate, amount, description, etc.")
        print("Type 'done' when finished, or 'help' for examples.")
        print("-"*60)
        
        columns = []
        while True:
            column = input(f"Column {len(columns) + 1}: ").strip()
            
            if column.lower() == 'done':
                if len(columns) == 0:
                    print("❌ Please enter at least one column name.")
                    continue
                break
            elif column.lower() == 'help':
                self._show_column_examples()
                continue
            elif column == '':
                print("❌ Column name cannot be empty.")
                continue
            elif column in columns:
                print(f"❌ Column '{column}' already exists.")
                continue
            
            columns.append(column)
            print(f"✅ Added column: {column}")
        
        print(f"\n✅ Created {len(columns)} columns: {', '.join(columns)}")
        return columns
    
    def _show_column_examples(self):
        """Show example column names."""
        print("\n📋 Common column examples:")
        print("  Invoice columns: invoice_no, date, vendor, total, tax")
        print("  Item columns: sr.no, particulars, description, qty, rate, amount")
        print("  Address columns: billing_address, shipping_address")
        print("  Payment columns: payment_terms, due_date, bank_details")
        print("  Custom columns: Any name you want (e.g., 'project_code', 'notes')")
        print()
    
    def analyze_extracted_data(self, results: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Analyze extracted data and categorize potential values.
        
        Args:
            results: Results from document processing
            
        Returns:
            Dict with categorized data
        """
        self.extracted_data = results
        
        categorized = {
            'numbers': [],
            'amounts': [],
            'dates': [],
            'serial_numbers': [],
            'descriptions': [],
            'addresses': [],
            'emails': [],
            'phone_numbers': [],
            'company_names': [],
            'other_text': [],
            'tables': results.get('tables', [])  # Store tables for structured mapping
        }
        
        # Analyze text blocks
        for block in results.get('text_blocks', []):
            text = block['text'].strip()
            if not text:
                continue
                
            # Categorize based on patterns
            if self._is_amount(text):
                categorized['amounts'].append(text)
            elif self._is_date(text):
                categorized['dates'].append(text)
            elif self._is_serial_number(text):
                categorized['serial_numbers'].append(text)
            elif self._is_email(text):
                categorized['emails'].append(text)
            elif self._is_phone_number(text):
                categorized['phone_numbers'].append(text)
            elif self._is_number(text):
                categorized['numbers'].append(text)
            elif self._is_address(text):
                categorized['addresses'].append(text)
            elif self._is_company_name(text):
                categorized['company_names'].append(text)
            else:
                categorized['descriptions'].append(text)
        
        # Analyze key-value pairs
        for kv in results.get('key_value_pairs', []):
            key = kv['key'].strip()
            value = kv['value'].strip()
            
            if not value:
                continue
                
            # Store key-value relationships
            if key and value:
                if key not in categorized:
                    categorized[key] = []
                categorized[key].append(value)
        
        return categorized
    
    def map_columns_to_data(self, columns: List[str], categorized_data: Dict[str, List[str]], use_tables: bool = True) -> Dict[str, List[str]]:
        """
        Map user columns to extracted data using intelligent matching.
        Prioritizes table data when available for better structure.
        
        Args:
            columns: User-defined column names
            categorized_data: Categorized extracted data
            use_tables: Whether to use table data if available
            
        Returns:
            Dict mapping columns to matched values
        """
        # First, try to map from tables if available
        if use_tables and categorized_data.get('tables'):
            table_mappings = self._map_columns_from_tables(columns, categorized_data['tables'])
            if table_mappings and any(len(v) > 0 for v in table_mappings.values()):
                # Use table mappings if we found data
                return table_mappings
        
        # Fall back to text-based mapping
        mappings = {}
        
        for column in columns:
            print(f"\n🔍 Finding data for column: '{column}'")
            
            # Find best matches for this column
            matches = self._find_best_matches(column, categorized_data)
            
            if matches:
                print(f"   Found {len(matches)} potential values:")
                for i, match in enumerate(matches[:5], 1):  # Show top 5
                    print(f"   {i}. {match}")
                if len(matches) > 5:
                    print(f"   ... and {len(matches) - 5} more")
                
                mappings[column] = matches
            else:
                print(f"   ❌ No matches found")
                mappings[column] = []
        
        return mappings
    
    def _map_columns_from_tables(self, columns: List[str], tables: List[List[List[str]]]) -> Dict[str, List[str]]:
        """
        Map columns to table data by matching column names to table headers.
        Prioritizes line item tables (tables with description, qty, price columns).
        Uses AI if available for better accuracy.
        
        Args:
            columns: User-defined column names
            tables: List of tables (each table is a list of rows)
            
        Returns:
            Dict mapping columns to values from tables
        """
        mappings = {col: [] for col in columns}
        
        if not tables:
            return mappings
        
        # Extract table headers
        table_headers = []
        for table in tables:
            if table and len(table) > 0:
                table_headers.append(table[0])
            else:
                table_headers.append([])
        
        # Use AI mapping if available
        if self.use_ai and self.ai_mapper:
            try:
                # Pass sample table rows for better context
                ai_mappings = self.ai_mapper.map_columns_intelligently(
                    columns, 
                    table_headers,
                    sample_data=self.extracted_data,
                    sample_rows=tables  # Pass actual table data for context
                )
                
                # Extract data using AI mappings - row by row to maintain alignment
                # Find the table with the most mappings (likely the line items table)
                table_usage = {}
                for user_col, (table_idx, col_idx) in ai_mappings.items():
                    table_usage[table_idx] = table_usage.get(table_idx, 0) + 1
                
                primary_table_idx = max(table_usage.items(), key=lambda x: x[1])[0] if table_usage else 0
                
                if primary_table_idx < len(tables):
                    primary_table = tables[primary_table_idx]
                    if len(primary_table) > 1:
                        # Extract row by row to maintain alignment
                        for row_idx, row in enumerate(primary_table[1:], 1):  # Skip header
                            # Skip summary rows
                            row_cells = [str(c).strip() for c in row if c and str(c).strip()]
                            if len(row_cells) < 2:
                                continue
                            
                            row_text = ' '.join(cell.lower() for cell in row_cells)
                            # Skip rows that are clearly summaries
                            if any(word in row_text for word in ['total', 'subtotal', 'grand total']) and len(row_cells) <= 3:
                                # But allow if first column has product description
                                if len(row) > 0 and not str(row[0]).strip():
                                    continue
                            
                            # Extract each column's value for this row
                            for user_col, (table_idx, col_idx) in ai_mappings.items():
                                if table_idx == primary_table_idx and col_idx < len(row):
                                    cell_value = str(row[col_idx]).strip() if row[col_idx] else ''
                                    if cell_value and cell_value.lower() not in ['total', 'subtotal', 'invoice', '', 'none']:
                                        # Ensure we have the right number of values (pad if needed)
                                        current_count = len(mappings.get(user_col, []))
                                        if row_idx > current_count:
                                            # Pad previous rows with empty values
                                            while len(mappings.get(user_col, [])) < row_idx - 1:
                                                mappings.setdefault(user_col, []).append('')
                                        mappings.setdefault(user_col, []).append(cell_value)
                
                # If AI found mappings, use them
                if any(len(v) > 0 for v in mappings.values()):
                    # Validate with AI
                    sample_rows = [table[1:3] for table in tables if len(table) > 1][:1]  # First 2 data rows
                    if sample_rows:
                        mappings = self.ai_mapper.validate_and_correct_mapping(
                            mappings, columns, sample_rows[0] if sample_rows else None
                        )
                    return mappings
            except Exception as e:
                print(f"⚠️  AI mapping error: {e}. Falling back to rule-based mapping.")
        
        # Fallback to rule-based mapping
        best_table = self._find_line_items_table(tables, columns)
        
        if not best_table:
            # If no line items table found, try all tables
            for table in tables:
                if not table or len(table) < 2:
                    continue
                self._extract_from_table(table, columns, mappings)
        else:
            # Use the best table
            self._extract_from_table(best_table, columns, mappings)
        
        return mappings
    
    def _find_line_items_table(self, tables: List[List[List[str]]], columns: List[str]) -> List[List[str]]:
        """Find the table that looks most like a line items table."""
        line_item_keywords = ['description', 'qty', 'quantity', 'price', 'amount', 'item', 'product', 'service']
        
        best_table = None
        best_score = 0
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            header_row = table[0]
            header_lower = ' '.join([h.lower().strip() for h in header_row])
            
            # Score based on how many line item keywords appear in headers
            score = sum(1 for keyword in line_item_keywords if keyword in header_lower)
            
            # Bonus if table has multiple data rows (not just header + summary)
            if len(table) > 2:
                score += 1
            
            if score > best_score:
                best_score = score
                best_table = table
        
        return best_table
    
    def _extract_from_table(self, table: List[List[str]], columns: List[str], mappings: Dict[str, List[str]]):
        """Extract data from a single table."""
        if not table or len(table) < 2:
            return
        
        # First row is usually header
        header_row = table[0]
        header_lower = [h.lower().strip() for h in header_row]
        
        # Map user columns to table column indices (one-to-one mapping)
        # First pass: collect all potential matches with scores
        potential_matches = []
        for user_col in columns:
            user_col_lower = user_col.lower()
            for header_idx, header in enumerate(header_lower):
                match_score = self._calculate_match_score(user_col_lower, header)
                if match_score > 0.5:  # Threshold
                    potential_matches.append((user_col, header_idx, match_score))
        
        # Sort by score (highest first)
        potential_matches.sort(key=lambda x: x[2], reverse=True)
        
        # Assign matches (one-to-one, best scores first)
        column_to_table_index = {}
        used_indices = set()
        used_columns = set()
        
        for user_col, header_idx, score in potential_matches:
            if user_col not in used_columns and header_idx not in used_indices:
                column_to_table_index[user_col] = header_idx
                used_indices.add(header_idx)
                used_columns.add(user_col)
        
        # Extract data rows (skip header, and skip summary rows at the end)
        data_rows = table[1:]
        
        # Filter out summary rows (rows that are mostly empty or contain totals)
        filtered_rows = []
        for row in data_rows:
            # Skip rows that are mostly empty
            non_empty_cells = sum(1 for cell in row if cell.strip())
            if non_empty_cells < 2:
                continue
            
            # Skip rows that look like summary rows (contain "total", "subtotal", etc.)
            row_text = ' '.join(cell.lower() for cell in row)
            if any(word in row_text for word in ['total', 'subtotal', 'grand total', 'invoice total']):
                # Only skip if it's clearly a summary (not a product name with "total" in it)
                if len([c for c in row if c.strip()]) <= 2:
                    continue
            
            filtered_rows.append(row)
        
        # Extract data from filtered rows
        for row in filtered_rows:
            for user_col in columns:
                if user_col in column_to_table_index:
                    col_idx = column_to_table_index[user_col]
                    if col_idx < len(row):
                        cell_value = row[col_idx].strip()
                        if cell_value and cell_value.lower() not in ['total', 'subtotal', 'invoice', '']:
                            mappings[user_col].append(cell_value)
    
    def _calculate_match_score(self, user_col: str, table_header: str) -> float:
        """Calculate a match score between user column and table header (0.0 to 1.0)."""
        user_col_lower = user_col.lower().strip()
        table_header_lower = table_header.lower().strip()
        
        # Exact match
        if user_col_lower == table_header_lower:
            return 1.0
        
        # Direct substring match
        if user_col_lower in table_header_lower:
            return 0.9
        if table_header_lower in user_col_lower:
            return 0.8
        
        # Alias matching with scores
        aliases = {
            'sr.no': [('sr no', 1.0), ('s.no', 0.9), ('serial no', 0.8), ('sno', 0.8), ('no', 0.6), ('number', 0.5)],
            'particulars': [('description', 1.0), ('item description', 0.9), ('item', 0.8), ('product', 0.8), ('service', 0.8)],
            'description': [('description', 1.0), ('item description', 0.9), ('particulars', 0.9), ('item', 0.8)],
            'qty': [('qty', 1.0), ('quantity', 1.0), ('qnty', 0.9), ('q', 0.7)],
            'quantity': [('quantity', 1.0), ('qty', 1.0), ('qnty', 0.9)],
            'rate': [('unit price', 0.9), ('price', 0.8), ('rate', 1.0), ('cost', 0.7), ('per unit', 0.6)],
            'amount': [('item subtotal', 0.95), ('item subtotal (incl. vat)', 1.0), ('item subtotal (excl. vat)', 0.9), ('subtotal', 0.8), ('amount', 1.0), ('total', 0.6)],
            'total': [('total', 1.0), ('grand total', 0.9), ('invoice total', 0.9), ('amount', 0.7)],
            'date': [('date', 1.0), ('dated', 0.9), ('invoice date', 0.9), ('order date', 0.8)],
            'invoice_no': [('invoice', 0.9), ('invoice number', 1.0), ('invoice #', 0.9), ('inv no', 0.8)],
            'tax': [('vat', 0.9), ('vat rate', 0.9), ('tax', 1.0), ('tax rate', 0.9), ('gst', 0.8)]
        }
        
        if user_col_lower in aliases:
            for alias, score in aliases[user_col_lower]:
                # Check if alias appears in header (case-insensitive, word boundary aware)
                if alias in table_header_lower:
                    # Prefer exact word match
                    import re
                    if re.search(r'\b' + re.escape(alias) + r'\b', table_header_lower):
                        return score
                    else:
                        return score * 0.8  # Slightly lower score for substring match
        
        # Word overlap
        user_words = set(word for word in user_col_lower.split() if len(word) > 2)
        header_words = set(word for word in table_header_lower.split() if len(word) > 2)
        
        if user_words and header_words:
            overlap = user_words.intersection(header_words)
            if overlap:
                return min(0.6, len(overlap) / max(len(user_words), 1))
        
        return 0.0
    
    def _columns_match(self, user_col: str, table_header: str) -> bool:
        """Check if user column name matches table header."""
        user_col_lower = user_col.lower().strip()
        table_header_lower = table_header.lower().strip()
        
        # Exact match
        if user_col_lower == table_header_lower:
            return True
        
        # Partial match (user column contains header or vice versa)
        if user_col_lower in table_header_lower or table_header_lower in user_col_lower:
            return True
        
        # Common aliases with more comprehensive matching
        aliases = {
            'sr.no': ['sr no', 's.no', 'serial no', 'sno', 'no', 'number', '#', 'item no', 'line no'],
            'particulars': ['description', 'item', 'product', 'service', 'details', 'particulars', 'item description'],
            'description': ['description', 'particulars', 'item', 'product', 'service', 'details', 'item description'],
            'product': ['description', 'item description', 'item', 'product', 'service', 'details', 'particulars'],
            'qty': ['quantity', 'qty', 'qnty', 'q', 'qty.', 'qunatity'],
            'quantity': ['quantity', 'qty', 'qnty', 'q', 'qty.', 'qunatity'],
            'rate': ['price', 'unit price', 'rate', 'cost', 'per unit', 'unit cost', 'price per unit', 
                    'unit price (excl. vat)', 'unit price (incl. vat)', 'excl. vat', 'incl. vat'],
            'amount': ['total', 'amount', 'amt', 'sum', 'value', 'item subtotal', 'subtotal', 
                      'item subtotal (incl. vat)', 'item subtotal (excl. vat)'],
            'total': ['amount', 'total', 'sum', 'grand total', 'invoice total', 'total amount'],
            'date': ['date', 'dated', 'invoice date', 'bill date', 'order date', 'delivery date'],
            'invoice_no': ['invoice', 'inv no', 'invoice number', 'bill no', 'bill number', 'invoice #', 'inv#'],
            'tax': ['vat', 'tax', 'vat rate', 'tax rate', 'vat subtotal', 'tax amount', 'gst']
        }
        
        if user_col_lower in aliases:
            for alias in aliases[user_col_lower]:
                # Check if alias appears in table header
                if alias in table_header_lower:
                    return True
                # Also check if any word from alias appears
                alias_words = alias.split()
                if any(word in table_header_lower for word in alias_words if len(word) > 2):
                    return True
        
        # Word-based matching (check if key words match)
        user_words = set(word for word in user_col_lower.split() if len(word) > 2)
        header_words = set(word for word in table_header_lower.split() if len(word) > 2)
        
        # If significant words overlap, consider it a match
        if user_words and header_words:
            overlap = user_words.intersection(header_words)
            if len(overlap) >= min(len(user_words), 1):
                return True
        
        return False
    
    def _find_best_matches(self, column: str, categorized_data: Dict[str, List[str]]) -> List[str]:
        """
        Find best matching data for a column using various strategies.
        
        Args:
            column: Column name to match
            categorized_data: Categorized data
            
        Returns:
            List of matching values
        """
        column_lower = column.lower()
        matches = []
        
        # Strategy 1: Direct keyword matching
        keyword_matches = self._match_by_keywords(column_lower, categorized_data)
        matches.extend(keyword_matches)
        
        # Strategy 2: Pattern matching
        pattern_matches = self._match_by_patterns(column_lower, categorized_data)
        matches.extend(pattern_matches)
        
        # Strategy 3: Fuzzy string matching with key-value pairs
        fuzzy_matches = self._match_by_fuzzy_keys(column_lower, categorized_data)
        matches.extend(fuzzy_matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for match in matches:
            if match not in seen:
                seen.add(match)
                unique_matches.append(match)
        
        return unique_matches
    
    def _match_by_keywords(self, column: str, data: Dict[str, List[str]]) -> List[str]:
        """Match by keyword patterns."""
        matches = []
        
        # Define keyword mappings
        keyword_map = {
            'sr.no': ['serial_numbers', 'numbers'],
            'serial': ['serial_numbers', 'numbers'],
            'sno': ['serial_numbers', 'numbers'],
            'particulars': ['descriptions', 'other_text'],
            'description': ['descriptions', 'other_text'],
            'qty': ['numbers'],
            'quantity': ['numbers'],
            'rate': ['amounts', 'numbers'],
            'price': ['amounts', 'numbers'],
            'amount': ['amounts'],
            'total': ['amounts'],
            'date': ['dates'],
            'invoice': ['serial_numbers', 'numbers'],
            'email': ['emails'],
            'phone': ['phone_numbers'],
            'address': ['addresses'],
            'company': ['company_names'],
            'vendor': ['company_names'],
            'supplier': ['company_names']
        }
        
        # Check if column matches any keywords
        for keyword, categories in keyword_map.items():
            if keyword in column:
                for category in categories:
                    if category in data:
                        matches.extend(data[category])
                break
        
        return matches
    
    def _match_by_patterns(self, column: str, data: Dict[str, List[str]]) -> List[str]:
        """Match by data type patterns."""
        matches = []
        
        # Pattern-based matching
        if any(word in column for word in ['amount', 'total', 'price', 'rate', 'cost']):
            matches.extend(data.get('amounts', []))
        elif any(word in column for word in ['qty', 'quantity', 'count', 'number']):
            matches.extend(data.get('numbers', []))
        elif any(word in column for word in ['date', 'time']):
            matches.extend(data.get('dates', []))
        elif any(word in column for word in ['email', 'mail']):
            matches.extend(data.get('emails', []))
        elif any(word in column for word in ['phone', 'mobile', 'contact']):
            matches.extend(data.get('phone_numbers', []))
        elif any(word in column for word in ['address', 'location']):
            matches.extend(data.get('addresses', []))
        
        return matches
    
    def _match_by_fuzzy_keys(self, column: str, data: Dict[str, List[str]]) -> List[str]:
        """Match using fuzzy string matching on key-value pair keys."""
        matches = []
        threshold = 0.6  # Similarity threshold
        
        for key, values in data.items():
            if key in ['numbers', 'amounts', 'dates', 'serial_numbers', 'descriptions', 
                      'addresses', 'emails', 'phone_numbers', 'company_names', 'other_text']:
                continue  # Skip category keys
            
            # Calculate similarity between column and key
            similarity = SequenceMatcher(None, column.lower(), key.lower()).ratio()
            if similarity >= threshold:
                matches.extend(values)
        
        return matches
    
    def create_csv_output(self, columns: List[str], mappings: Dict[str, List[str]], output_file: str) -> str:
        """
        Create CSV file from mapped data.
        
        Args:
            columns: Column names
            mappings: Column to data mappings
            output_file: Output CSV file path
            
        Returns:
            Path to created CSV file
        """
        # Determine number of rows needed
        max_rows = max(len(values) for values in mappings.values()) if mappings else 1
        
        # Create CSV data
        csv_data = []
        
        # Add header
        csv_data.append(columns)
        
        # Add data rows
        for row_idx in range(max_rows):
            row = []
            for column in columns:
                values = mappings.get(column, [])
                if row_idx < len(values):
                    row.append(values[row_idx])
                else:
                    row.append('')  # Empty cell if no data
            csv_data.append(row)
        
        # Write CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(csv_data)
        
        return output_file
    
    def print_mapping_summary(self, columns: List[str], mappings: Dict[str, List[str]]):
        """Print summary of column mappings."""
        print("\n" + "="*60)
        print("COLUMN MAPPING SUMMARY")
        print("="*60)
        
        for column in columns:
            values = mappings.get(column, [])
            print(f"\n📋 {column}:")
            if values:
                print(f"   ✅ Found {len(values)} values")
                for i, value in enumerate(values[:3], 1):
                    print(f"   {i}. {value}")
                if len(values) > 3:
                    print(f"   ... and {len(values) - 3} more")
            else:
                print(f"   ❌ No values found")
        
        print("\n" + "="*60)
    
    # Helper methods for data type detection
    def _is_amount(self, text: str) -> bool:
        """Check if text represents a monetary amount."""
        # Remove common currency symbols and separators
        cleaned = re.sub(r'[₹$€£,\s]', '', text)
        return bool(re.match(r'^\d+\.?\d*$', cleaned)) and ('.' in text or ',' in text or any(c in text for c in '₹$€£'))
    
    def _is_date(self, text: str) -> bool:
        """Check if text represents a date."""
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{2,4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}'
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _is_serial_number(self, text: str) -> bool:
        """Check if text represents a serial number."""
        # Simple serial numbers (1, 2, 3, etc.) or alphanumeric codes
        return bool(re.match(r'^\d+$', text.strip())) or bool(re.match(r'^[A-Z0-9\-]+$', text.strip()))
    
    def _is_email(self, text: str) -> bool:
        """Check if text is an email address."""
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text.strip()))
    
    def _is_phone_number(self, text: str) -> bool:
        """Check if text is a phone number."""
        cleaned = re.sub(r'[\s\-\(\)\+]', '', text)
        return bool(re.match(r'^\d{10,15}$', cleaned))
    
    def _is_number(self, text: str) -> bool:
        """Check if text is a simple number."""
        try:
            float(text.replace(',', ''))
            return True
        except ValueError:
            return False
    
    def _is_address(self, text: str) -> bool:
        """Check if text looks like an address."""
        address_keywords = ['street', 'road', 'avenue', 'lane', 'nagar', 'colony', 'sector', 'block', 'house', 'no', 'plot']
        return any(keyword in text.lower() for keyword in address_keywords) or len(text.split()) > 3
    
    def _is_company_name(self, text: str) -> bool:
        """Check if text looks like a company name."""
        company_keywords = ['ltd', 'limited', 'pvt', 'private', 'corp', 'corporation', 'inc', 'systems', 'solutions', 'services']
        return any(keyword in text.lower() for keyword in company_keywords) or text.isupper()