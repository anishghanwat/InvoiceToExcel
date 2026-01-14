"""
Layer A: Deterministic Mapping (NO AI)
Maps Textract fields to canonical schema using rules.
Fast, predictable, no AI needed.
"""
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class DeterministicMapper:
    """Rule-based mapping from Textract to canonical schema."""
    
    def __init__(self):
        """Initialize deterministic mapper."""
        self.canonical_schema = {
            'invoice_number': None,
            'invoice_date': None,
            'vendor': None,
            'customer': None,
            'order_number': None,
            'payment_terms': None,
            'tax_id': None,
            'currency': None,
            'subtotal': None,
            'tax_amount': None,
            'tax_rate': None,
            'total_amount': None,
            'line_items': []
        }
    
    def map_to_canonical(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Textract results to canonical schema using deterministic rules.
        
        Args:
            results: Textract extraction results
            
        Returns:
            Canonical schema with mapped fields
        """
        canonical = self.canonical_schema.copy()
        
        # Extract from key-value pairs
        kv_pairs = results.get('key_value_pairs', [])
        for kv in kv_pairs:
            key = kv['key'].strip()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            key_lower = key.lower()
            
            # Map to canonical fields using rules
            if self._matches_invoice_number(key_lower):
                canonical['invoice_number'] = self._normalize_invoice_number(value)
            
            elif self._matches_date(key_lower):
                canonical['invoice_date'] = self._normalize_date(value)
            
            elif self._matches_vendor(key_lower):
                canonical['vendor'] = self._normalize_text(value)
            
            elif self._matches_customer(key_lower):
                # Only set if value doesn't look like an amount
                if not self._looks_like_amount(value):
                    canonical['customer'] = self._normalize_text(value)
            
            elif self._matches_order_number(key_lower):
                canonical['order_number'] = value.strip()
            
            elif self._matches_tax_id(key_lower):
                # Only set if value doesn't look like an amount or percentage
                if not self._looks_like_amount(value) and '%' not in value:
                    canonical['tax_id'] = self._normalize_text(value)
            
            elif self._matches_total(key_lower):
                amount = self._normalize_amount(value)
                if amount and not canonical['total_amount']:
                    canonical['total_amount'] = amount
            
            elif self._matches_subtotal(key_lower):
                amount = self._normalize_amount(value)
                if amount:
                    canonical['subtotal'] = amount
            
            elif self._matches_tax(key_lower):
                amount = self._normalize_amount(value)
                if amount:
                    canonical['tax_amount'] = amount
            
            elif self._matches_tax_rate(key_lower):
                canonical['tax_rate'] = self._normalize_percentage(value)
        
        # Extract currency
        canonical['currency'] = self._detect_currency(results)
        
        # Extract line items from tables (deterministic)
        canonical['line_items'] = self._extract_line_items_deterministic(results)
        
        # Extract totals from tables if not found in key-value pairs
        if not canonical['total_amount']:
            canonical['total_amount'] = self._extract_total_from_tables(results)
        if not canonical['subtotal']:
            canonical['subtotal'] = self._extract_subtotal_from_tables(results)
        if not canonical['tax_amount']:
            canonical['tax_amount'] = self._extract_tax_from_tables(results)
        
        return canonical
    
    def _extract_total_from_tables(self, results: Dict[str, Any]) -> Optional[float]:
        """Extract total amount from tables."""
        tables = results.get('tables', [])
        for table in tables:
            if not table or len(table) < 2:
                continue
            # Look for "Total" or "Grand Total" rows
            for row in table:
                row_text = ' '.join(str(cell).lower() for cell in row if cell)
                if any(word in row_text for word in ['total', 'grand total', 'amount due']):
                    # Extract amount from the row
                    for cell in row:
                        amount = self._normalize_amount(str(cell))
                        if amount and amount > 0:
                            return amount
        return None
    
    def _extract_subtotal_from_tables(self, results: Dict[str, Any]) -> Optional[float]:
        """Extract subtotal from tables."""
        tables = results.get('tables', [])
        for table in tables:
            if not table or len(table) < 2:
                continue
            for row in table:
                row_text = ' '.join(str(cell).lower() for cell in row if cell)
                if 'subtotal' in row_text:
                    for cell in row:
                        amount = self._normalize_amount(str(cell))
                        if amount and amount > 0:
                            return amount
        return None
    
    def _extract_tax_from_tables(self, results: Dict[str, Any]) -> Optional[float]:
        """Extract tax amount from tables."""
        tables = results.get('tables', [])
        for table in tables:
            if not table or len(table) < 2:
                continue
            for row in table:
                row_text = ' '.join(str(cell).lower() for cell in row if cell)
                if any(word in row_text for word in ['tax', 'vat', 'gst']) and 'rate' not in row_text:
                    # Look for amount in cells that contain currency symbols or reasonable amounts
                    for cell in row:
                        cell_str = str(cell)
                        # Skip if it looks like an ID (long number, no currency symbol)
                        if len(cell_str) > 10 and not any(symbol in cell_str for symbol in ['£', '$', '€', '₹', 'Rs']):
                            continue
                        amount = self._normalize_amount(cell_str)
                        # Tax amounts should be reasonable (not millions)
                        if amount and 0 < amount < 1000000:
                            return amount
        return None
    
    def _matches_invoice_number(self, key: str) -> bool:
        """Check if key matches invoice number pattern."""
        patterns = ['invoice', 'inv no', 'invoice #', 'bill no', 'invoice number']
        return any(pattern in key for pattern in patterns)
    
    def _matches_date(self, key: str) -> bool:
        """Check if key matches date pattern."""
        patterns = ['date', 'dated', 'invoice date', 'bill date', 'invoice date']
        return any(pattern in key for pattern in patterns)
    
    def _matches_vendor(self, key: str) -> bool:
        """Check if key matches vendor pattern."""
        patterns = ['vendor', 'supplier', 'from', 'seller', 'sold by']
        return any(pattern in key for pattern in patterns)
    
    def _matches_customer(self, key: str) -> bool:
        """Check if key matches customer pattern."""
        patterns = ['customer', 'bill to', 'to', 'buyer', 'billing address', 'delivery address']
        return any(pattern in key for pattern in patterns)
    
    def _matches_order_number(self, key: str) -> bool:
        """Check if key matches order number pattern."""
        patterns = ['order', 'order #', 'order no', 'po number', 'p.o.']
        return any(pattern in key for pattern in patterns)
    
    def _matches_tax_id(self, key: str) -> bool:
        """Check if key matches tax ID pattern."""
        patterns = ['vat', 'tax id', 'gstin', 'tax number', 'vat #', 'gst']
        return any(pattern in key for pattern in patterns)
    
    def _matches_total(self, key: str) -> bool:
        """Check if key matches total pattern."""
        patterns = ['total', 'grand total', 'invoice total', 'total payable', 'amount due']
        return any(pattern in key for pattern in patterns)
    
    def _matches_subtotal(self, key: str) -> bool:
        """Check if key matches subtotal pattern."""
        patterns = ['subtotal', 'total (excl', 'excl. tax', 'excl tax']
        return any(pattern in key for pattern in patterns)
    
    def _matches_tax(self, key: str) -> bool:
        """Check if key matches tax amount pattern."""
        patterns = ['tax', 'vat', 'gst', 'tax amount', 'vat amount', 'tax total']
        return any(pattern in key for pattern in patterns) and 'rate' not in key
    
    def _matches_tax_rate(self, key: str) -> bool:
        """Check if key matches tax rate pattern."""
        patterns = ['tax rate', 'vat rate', 'gst rate', 'tax %', 'vat %']
        return any(pattern in key for pattern in patterns)
    
    def _normalize_invoice_number(self, value: str) -> str:
        """Normalize invoice number."""
        return value.strip().upper()
    
    def _normalize_date(self, value: str) -> Optional[str]:
        """Normalize date to ISO format."""
        # Try to parse common date formats
        date_patterns = [
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',
            r'(\d{2,4})[-/](\d{1,2})[-/](\d{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, value)
            if match:
                # Return as-is for now, can be improved
                return value.strip()
        
        return value.strip()
    
    def _normalize_text(self, value: str) -> str:
        """Normalize text field."""
        return value.strip()
    
    def _normalize_amount(self, value: str) -> Optional[float]:
        """Normalize monetary amount to float."""
        # Remove currency symbols
        cleaned = re.sub(r'[£$€₹Rs\.rs\.,\s]', '', str(value))
        # Handle cases like ".0.00"
        if cleaned.startswith('.'):
            cleaned = '0' + cleaned
        # Remove extra decimal points
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        # Keep only digits and decimal point
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _normalize_percentage(self, value: str) -> Optional[float]:
        """Normalize percentage to float."""
        cleaned = value.replace('%', '').strip()
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _looks_like_amount(self, value: str) -> bool:
        """Check if value looks like a monetary amount."""
        if not value:
            return False
        # Check for currency symbols or number patterns
        has_currency = any(symbol in value for symbol in ['£', '$', '€', '₹', 'Rs.', 'Rs'])
        has_number = bool(re.search(r'\d', value))
        return has_currency and has_number
    
    def _detect_currency(self, results: Dict[str, Any]) -> str:
        """Detect currency from document."""
        # Check key-value pairs and text blocks for currency symbols
        text_content = ' '.join([
            kv.get('value', '') for kv in results.get('key_value_pairs', [])
        ])
        
        if '£' in text_content:
            return 'GBP'
        elif '$' in text_content:
            return 'USD'
        elif '₹' in text_content or 'Rs.' in text_content:
            return 'INR'
        elif '€' in text_content:
            return 'EUR'
        else:
            return 'USD'  # Default
    
    def _extract_line_items_deterministic(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract line items using deterministic rules (no AI)."""
        line_items = []
        tables = results.get('tables', [])
        
        # Find line items table
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            headers = [h.lower().strip() for h in table[0]]
            header_text = ' '.join(headers)
            
            # Check if this is a line items table
            if any(word in header_text for word in ['description', 'item', 'product']):
                if any(word in header_text for word in ['qty', 'quantity', 'price', 'rate', 'amount']):
                    # Extract line items
                    for row in table[1:]:
                        item = self._parse_line_item_row(row, headers)
                        if item and item.get('description'):
                            line_items.append(item)
                    break
        
        return line_items
    
    def _parse_line_item_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single line item row deterministically."""
        item = {
            'description': '',
            'quantity': None,
            'unit_price': None,
            'amount': None,
            'tax_rate': None,
            'tax_amount': None
        }
        
        for col_idx, header in enumerate(headers):
            if col_idx >= len(row):
                continue
            
            value = str(row[col_idx]).strip() if row[col_idx] else ''
            if not value:
                continue
            
            # Map based on header
            if any(word in header for word in ['description', 'item', 'product', 'particulars']):
                item['description'] = value
            elif any(word in header for word in ['qty', 'quantity']):
                item['quantity'] = self._normalize_amount(value)
            elif any(word in header for word in ['rate', 'price', 'unit price']):
                item['unit_price'] = self._normalize_amount(value)
            elif any(word in header for word in ['amount', 'total', 'subtotal']):
                item['amount'] = self._normalize_amount(value)
            elif any(word in header for word in ['tax rate', 'vat rate']):
                item['tax_rate'] = self._normalize_percentage(value)
            elif any(word in header for word in ['tax', 'vat']):
                item['tax_amount'] = self._normalize_amount(value)
        
        return item if item['description'] else None
