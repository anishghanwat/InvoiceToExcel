"""
Professional Invoice CSV Mapper - Creates audit-ready invoice CSV files
with proper structure, complete data, and professional formatting.

Now uses the 4-layer normalization pipeline for accurate data extraction.
"""
import csv
import json
import re
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.normalization.normalization_pipeline import NormalizationPipeline


class ProfessionalCSVMapper:
    """Creates professional, audit-ready invoice CSV files using normalization pipeline."""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize the professional CSV mapper.
        
        Args:
            use_ai: Whether to use AI layers in normalization
        """
        self.normalization_pipeline = NormalizationPipeline(use_ai=use_ai)
        self.invoice_data = {}
        self.line_items = []
    
    def extract_invoice_structure(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract complete invoice structure using normalization pipeline.
        
        Returns structured invoice data ready for CSV export.
        """
        # Get document text for context
        document_text = ' '.join([
            block.get('text', '') for block in results.get('text_blocks', [])[:50]
        ])
        
        # Run normalization pipeline
        normalized = self.normalization_pipeline.normalize(results, document_text)
        canonical = normalized['canonical']
        validation = normalized['validation']
        
        # Convert canonical format to invoice structure format
        invoice_header = {
            'invoice_number': canonical.get('invoice_number', ''),
            'invoice_date': canonical.get('invoice_date', ''),
            'vendor': canonical.get('vendor', ''),
            'customer': canonical.get('customer', ''),
            'order_number': canonical.get('order_number', ''),
            'payment_terms': canonical.get('payment_terms', ''),
            'tax_id': canonical.get('tax_id', ''),
            'currency': canonical.get('currency', '')
        }
        
        # Convert line items format
        line_items = []
        normalized_items = canonical.get('line_items', [])
        
        # Check if normalized items are valid (have proper descriptions)
        valid_normalized_items = [
            item for item in normalized_items 
            if item.get('description') and not self._is_amount(str(item.get('description', '')))
        ]
        
        # If normalization didn't extract line items well, fall back to old method
        if not valid_normalized_items:
            # Use old extraction method as fallback
            line_items = self._extract_line_items_old(results)
        else:
            for idx, item in enumerate(valid_normalized_items, 1):
                description = item.get('description', '').strip()
                if not description:
                    continue
                
                line_items.append({
                    'line_number': str(idx),
                    'description': description,
                    'quantity': str(item.get('quantity', '')) if item.get('quantity') else '',
                    'unit_price': f"{item.get('unit_price', 0):.2f}" if item.get('unit_price') else '',
                    'amount': f"{item.get('amount', 0):.2f}" if item.get('amount') else '',
                    'tax_rate': f"{item.get('tax_rate', 0)}%" if item.get('tax_rate') else '',
                    'tax_amount': f"{item.get('tax_amount', 0):.2f}" if item.get('tax_amount') else '',
                    'total': self._calculate_line_item_total(item)
                })
        
        # Extract totals
        totals = {
            'subtotal': f"{canonical.get('subtotal', 0):.2f}" if canonical.get('subtotal') else '',
            'tax_total': f"{canonical.get('tax_amount', 0):.2f}" if canonical.get('tax_amount') else '',
            'total': f"{canonical.get('total_amount', 0):.2f}" if canonical.get('total_amount') else ''
        }
        
        return {
            'header': invoice_header,
            'line_items': line_items,
            'totals': totals,
            'validation': validation
        }
    
    def _calculate_line_item_total(self, item: Dict[str, Any]) -> str:
        """Calculate total for a line item."""
        try:
            amount = float(item.get('amount', 0) or 0)
            tax_amount = float(item.get('tax_amount', 0) or 0)
            total = amount + tax_amount
            return f"{total:.2f}" if total > 0 else ''
        except (ValueError, TypeError):
            return ''
    
    def _is_amount(self, value: str) -> bool:
        """Check if value looks like an amount."""
        if not value:
            return False
        # Remove currency symbols
        cleaned = re.sub(r'[£$€₹,\s]', '', str(value))
        # Check if it's a number
        try:
            float(cleaned)
            return True
        except:
            return False
    
    def _extract_invoice_header(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Extract invoice header information (invoice number, date, vendor, etc.)."""
        header = {}
        kv_pairs = results.get('key_value_pairs', [])
        
        # Common invoice header fields
        header_patterns = {
            'invoice_number': ['invoice', 'invoice #', 'invoice no', 'inv no', 'bill no', 'invoice number'],
            'invoice_date': ['invoice date', 'date', 'dated', 'bill date', 'invoice date / delivery date'],
            'order_number': ['order', 'order #', 'order no', 'order number', 'po number', 'p.o.'],
            'vendor': ['sold by', 'vendor', 'supplier', 'from', 'seller'],
            'customer': ['billing address', 'bill to', 'customer', 'to', 'buyer', 'delivery address'],
            'payment_terms': ['payment terms', 'terms', 'payment', 'due date'],
            'tax_id': ['vat', 'tax id', 'gstin', 'tax number', 'vat #'],
            'total_amount': ['total', 'total payable', 'grand total', 'invoice total', 'amount due']
        }
        
        # Extract from key-value pairs
        for kv in kv_pairs:
            key_lower = kv['key'].lower().strip()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            # Match to header fields
            for field, patterns in header_patterns.items():
                if any(pattern in key_lower for pattern in patterns):
                    if field not in header or len(value) > len(header.get(field, '')):
                        header[field] = value
        
        # Also extract from text blocks for missing fields
        if 'invoice_number' not in header:
            for block in results.get('text_blocks', [])[:20]:  # Check first 20 blocks
                text = block.get('text', '').strip()
                # Look for invoice number patterns
                if re.match(r'^[A-Z0-9\-]+$', text) and len(text) > 5:
                    if 'invoice_number' not in header:
                        header['invoice_number'] = text
                        break
        
        return header
    
    def _extract_line_items_old(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract line items from tables with proper structure."""
        line_items = []
        tables = results.get('tables', [])
        
        # Find the line items table (has Description, Qty, Price columns)
        # Try multiple strategies to find line items
        line_items_table = None
        best_score = 0
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            headers = [h.lower().strip() for h in table[0]]
            header_text = ' '.join(headers)
            
            # Score the table based on how much it looks like line items
            score = 0
            
            # Check for description/product column (case-insensitive, handle variations)
            desc_keywords = ['description', 'item', 'product', 'particulars', 'service', 'goods', 'name']
            has_description = any(keyword in header_text for keyword in desc_keywords)
            if has_description:
                score += 3
            
            # Check for quantity (handle QTY., Qty, etc.)
            qty_keywords = ['qty', 'quantity', 'qnty', 'qty.', 'qunatity']
            has_qty = any(keyword in header_text for keyword in qty_keywords)
            if has_qty:
                score += 2
            
            # Check for price/amount (handle RATE, Rate, etc.)
            price_keywords = ['price', 'rate', 'amount', 'cost', 'unit', 'total', 'value']
            has_price = any(keyword in header_text for keyword in price_keywords)
            if has_price:
                score += 2
            
            # Check for serial number (common in Indian invoices - SL NO., S.No, etc.)
            sr_keywords = ['sr', 's.no', 'serial', 'sl no', 'sl. no', 'sl no.', 's no', 's. no']
            has_sr_no = any(keyword in header_text for keyword in sr_keywords)
            if has_sr_no:
                score += 1
            
            # Bonus for tables with multiple data rows
            if len(table) > 2:
                score += 1
            
            # Bonus for tables with more columns (more likely to be line items)
            if len(headers) >= 4:
                score += 1
            
            if score > best_score and score >= 3:  # Lower threshold
                best_score = score
                line_items_table = table
        
        # If still no table found, try the largest table with data
        if not line_items_table:
            for table in tables:
                if not table or len(table) < 2:
                    continue
                # Use table with most rows and columns
                if len(table) > 2 and len(table[0]) >= 3:
                    line_items_table = table
                    break
        
        if not line_items_table:
            return line_items
        
        # Map headers to standard fields
        headers = line_items_table[0]
        header_map = self._map_table_headers(headers)
        
        # Extract data rows (skip header and summary rows)
        for row_idx, row in enumerate(line_items_table[1:], 1):
            # Skip summary/total rows - check if row is clearly a summary
            row_text = ' '.join(str(cell).lower() for cell in row if cell)
            non_empty = [c for c in row if c and str(c).strip()]
            
            # Skip if it's a summary row (has "total" and few cells, or first column is empty)
            if any(word in row_text for word in ['total', 'subtotal', 'grand total', 'invoice total']):
                if len(non_empty) <= 2 or (len(row) > 0 and not str(row[0]).strip()):
                    continue
            
            # Skip mostly empty rows (less than 2 meaningful cells)
            if len(non_empty) < 2:
                continue
            
            # Handle case where first column is serial number (SL NO., S.No, etc.)
            # Check if first column is a serial number
            first_cell = str(row[0]).strip() if len(row) > 0 else ''
            is_serial_number = first_cell.isdigit() and len(first_cell) <= 3
            
            # Find description column - could be in first column OR next column if first is serial number
            has_description = False
            if is_serial_number:
                # Check columns 1 and 2 for description
                for idx in [1, 2]:
                    if idx < len(row) and row[idx]:
                        desc_cell = str(row[idx]).strip()
                        if desc_cell and len(desc_cell) > 1 and not self._is_amount(desc_cell):
                            has_description = True
                            break
            else:
                # First column should be description
                if first_cell and len(first_cell) > 1 and not self._is_amount(first_cell):
                    has_description = True
            
            # Skip if no description found
            if not has_description:
                continue
            
            # Extract line item
            line_item = {
                'line_number': str(row_idx),
                'description': '',
                'quantity': '',
                'unit_price': '',
                'amount': '',
                'tax_rate': '',
                'tax_amount': '',
                'total': ''
            }
            
            # Extract all available columns from the row
            for col_idx, cell in enumerate(row):
                if col_idx >= len(headers):
                    continue
                    
                header_lower = headers[col_idx].lower()
                value = str(cell).strip() if cell else ''
                
                if not value or value.lower() in ['total', 'subtotal', 'invoice', '']:
                    continue
                
                # Map based on header content (handle variations like SL NO., QTY., RATE, etc.)
                if any(word in header_lower for word in ['description', 'item', 'product', 'particulars', 'name']):
                    if not line_item['description']:
                        line_item['description'] = value
                # Also check if this column has description-like content when header doesn't match
                elif not line_item['description'] and len(value) > 3 and not self._is_amount(value):
                    # Might be description in a column without clear header
                    if col_idx > 0:  # Not first column (which might be serial number)
                        line_item['description'] = value
                
                elif any(word in header_lower for word in ['qty', 'quantity', 'qnty', 'qty.']):
                    line_item['quantity'] = self._clean_number(value)
                
                elif any(word in header_lower for word in ['rate', 'price', 'unit price']):
                    # Could be unit price or rate
                    if 'excl' in header_lower or 'excl.' in header_lower:
                        line_item['unit_price'] = self._clean_amount(value)
                        if not line_item['amount']:
                            line_item['amount'] = self._clean_amount(value)
                    elif not line_item['unit_price']:
                        # Assume it's unit price if we don't have one yet
                        line_item['unit_price'] = self._clean_amount(value)
                        if not line_item['amount']:
                            line_item['amount'] = self._clean_amount(value)
                
                elif any(word in header_lower for word in ['unit price (excl', 'price (excl', 'excl. vat', 'excl vat']):
                    line_item['unit_price'] = self._clean_amount(value)
                    if not line_item['amount']:
                        line_item['amount'] = self._clean_amount(value)
                
                elif any(word in header_lower for word in ['vat rate', 'tax rate', 'tax %', 'vat %', 'gst rate']):
                    line_item['tax_rate'] = self._clean_percentage(value)
                
                elif any(word in header_lower for word in ['item subtotal (incl', 'subtotal (incl', 'incl. vat', 'total']):
                    # This is the total including tax
                    total_val = self._clean_amount(value)
                    if total_val:
                        line_item['total'] = total_val
                        # If we have unit price excl VAT, calculate tax
                        if line_item['unit_price']:
                            unit_price_val = float(line_item['unit_price'])
                            total_val_num = float(total_val)
                            tax_amt = total_val_num - unit_price_val
                            if tax_amt > 0:
                                line_item['tax_amount'] = f"{tax_amt:.2f}"
                                line_item['amount'] = line_item['unit_price']
                        elif not line_item['amount']:
                            # Use total as amount if no unit price
                            line_item['amount'] = total_val
            
            # Calculate missing values
            try:
                unit_price = float(line_item['unit_price'] or '0')
                quantity = float(line_item['quantity'] or '1')
                amount = float(line_item['amount'] or '0')
                
                # Calculate amount if missing
                if not line_item['amount'] and unit_price and quantity:
                    calculated_amount = unit_price * quantity
                    line_item['amount'] = f"{calculated_amount:.2f}"
                    amount = calculated_amount
                
                # Calculate tax if we have rate but not amount
                if line_item['tax_rate'] and not line_item['tax_amount']:
                    tax_rate_val = float(line_item['tax_rate'].replace('%', ''))
                    if amount:
                        tax_amt = amount * (tax_rate_val / 100)
                        line_item['tax_amount'] = f"{tax_amt:.2f}"
                
                # Calculate total if missing
                if not line_item['total']:
                    amount_val = float(line_item['amount'] or '0')
                    tax_amt_val = float(line_item['tax_amount'] or '0')
                    line_item['total'] = f"{amount_val + tax_amt_val:.2f}"
                
            except (ValueError, TypeError) as e:
                # If calculations fail, use amount as total
                if line_item['amount'] and not line_item['total']:
                    line_item['total'] = line_item['amount']
            
            # Only add if has description and it's meaningful
            # Allow shorter descriptions (like "ITEM NAME 1") and allow if we have other data
            has_valid_data = (
                line_item['description'] and 
                len(line_item['description']) > 1 and 
                not self._is_amount(line_item['description'])
            ) or (
                # Allow if we have quantity, price, or total even without description
                (line_item['quantity'] or line_item['unit_price'] or line_item['total']) and
                line_item.get('line_number', '').isdigit()
            )
            
            if has_valid_data:
                # If no description but we have line number, use a placeholder
                if not line_item['description']:
                    line_item['description'] = f"Line Item {line_item.get('line_number', '')}"
                line_items.append(line_item)
        
        return line_items
    
    def _map_table_headers(self, headers: List[str]) -> Dict[str, int]:
        """Map table headers to standard field names."""
        header_map = {}
        header_lower = [h.lower().strip() for h in headers]
        
        for idx, header in enumerate(header_lower):
            # Description/Product
            if any(word in header for word in ['description', 'item', 'product', 'particulars', 'service']):
                if 'description' not in header_map:
                    header_map['description'] = idx
            
            # Quantity
            elif any(word in header for word in ['qty', 'quantity', 'qnty']):
                if 'quantity' not in header_map:
                    header_map['quantity'] = idx
            
            # Unit Price
            elif any(word in header for word in ['unit price', 'price', 'rate', 'cost', 'per unit']):
                if 'unit_price' not in header_map:
                    header_map['unit_price'] = idx
            
            # Amount/Subtotal
            elif any(word in header for word in ['item subtotal', 'subtotal', 'amount', 'total']):
                if 'amount' not in header_map and 'subtotal' not in header_map:
                    if 'item subtotal' in header or 'subtotal' in header:
                        header_map['subtotal'] = idx
                    else:
                        header_map['amount'] = idx
            
            # Tax Rate
            elif any(word in header for word in ['vat rate', 'tax rate', 'tax %', 'vat %', 'gst rate']):
                if 'tax_rate' not in header_map:
                    header_map['tax_rate'] = idx
            
            # Tax Amount
            elif any(word in header for word in ['vat subtotal', 'tax amount', 'vat amount', 'tax']):
                if 'tax_amount' not in header_map and 'tax_rate' not in header_map:
                    header_map['tax_amount'] = idx
        
        return header_map
    
    def _extract_totals_old(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Extract invoice totals and summary."""
        totals = {}
        kv_pairs = results.get('key_value_pairs', [])
        
        for kv in kv_pairs:
            key_lower = kv['key'].lower().strip()
            value = kv['value'].strip()
            
            if 'total' in key_lower or 'subtotal' in key_lower:
                if 'subtotal' in key_lower and 'subtotal' not in totals:
                    totals['subtotal'] = self._clean_amount(value)
                elif 'tax' in key_lower or 'vat' in key_lower:
                    totals['tax_total'] = self._clean_amount(value)
                elif 'total' in key_lower and 'total' not in totals:
                    totals['total'] = self._clean_amount(value)
        
        return totals
    
    def create_professional_csv(
        self, 
        invoice_structure: Dict[str, Any], 
        output_file: str,
        include_header: bool = True
    ) -> str:
        """
        Create professional, audit-ready invoice CSV.
        
        Structure:
        - Header row with invoice metadata (optional)
        - Column headers
        - Line items (one per row)
        - Summary row with totals
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            header = invoice_structure.get('header', {})
            line_items = invoice_structure.get('line_items', [])
            totals = invoice_structure.get('totals', {})
            
            # Write invoice header information (if requested)
            if include_header and header:
                writer.writerow(['Invoice Information'])
                for key, value in header.items():
                    writer.writerow([key.replace('_', ' ').title(), value])
                writer.writerow([])  # Empty row
            
            # Write column headers
            column_headers = [
                'Line #',
                'Description',
                'Quantity',
                'Unit Price',
                'Amount',
                'Tax Rate',
                'Tax Amount',
                'Total'
            ]
            writer.writerow(column_headers)
            
            # Write line items
            for item in line_items:
                row = [
                    item.get('line_number', ''),
                    item.get('description', ''),
                    item.get('quantity', ''),
                    item.get('unit_price', ''),
                    item.get('amount', ''),
                    item.get('tax_rate', ''),
                    item.get('tax_amount', ''),
                    item.get('total', '')
                ]
                writer.writerow(row)
            
            # Write summary row
            if totals or line_items:
                writer.writerow([])  # Empty row
                writer.writerow(['Summary'])
                
                # Calculate subtotal from line items
                subtotal = sum(float(item.get('amount', '0') or '0') for item in line_items)
                writer.writerow(['Subtotal (Excl. Tax)', '', '', '', '', '', '', f"{subtotal:.2f}"])
                
                # Calculate tax total
                tax_total = sum(float(item.get('tax_amount', '0') or '0') for item in line_items)
                if tax_total > 0:
                    writer.writerow(['Tax Total', '', '', '', '', '', '', f"{tax_total:.2f}"])
                elif 'tax_total' in totals:
                    writer.writerow(['Tax Total', '', '', '', '', '', '', totals['tax_total']])
                
                # Calculate grand total
                grand_total = sum(float(item.get('total', '0') or '0') for item in line_items)
                if grand_total > 0:
                    writer.writerow(['Grand Total (Incl. Tax)', '', '', '', '', '', '', f"{grand_total:.2f}"])
                elif 'total' in totals:
                    writer.writerow(['Grand Total', '', '', '', '', '', '', totals['total']])
        
        return output_file
    
    def create_flat_csv(
        self, 
        invoice_structure: Dict[str, Any], 
        output_file: str
    ) -> str:
        """
        Create flat CSV format - one row per line item with invoice header repeated.
        This is the standard format for accounting systems.
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            header = invoice_structure.get('header', {})
            line_items = invoice_structure.get('line_items', [])
            
            # Column headers - include invoice info + line item details
            column_headers = [
                'Invoice Number',
                'Invoice Date',
                'Vendor',
                'Customer',
                'Order Number',
                'Tax ID',
                'Line #',
                'Description',
                'Quantity',
                'Unit Price',
                'Amount',
                'Tax Rate',
                'Tax Amount',
                'Total'
            ]
            writer.writerow(column_headers)
            
            # Write line items with invoice header repeated
            for item in line_items:
                row = [
                    header.get('invoice_number', ''),
                    header.get('invoice_date', ''),
                    header.get('vendor', ''),
                    header.get('customer', ''),
                    header.get('order_number', ''),
                    header.get('tax_id', ''),
                    item.get('line_number', ''),
                    item.get('description', ''),
                    item.get('quantity', ''),
                    item.get('unit_price', ''),
                    item.get('amount', ''),
                    item.get('tax_rate', ''),
                    item.get('tax_amount', ''),
                    item.get('total', '')
                ]
                writer.writerow(row)
            
            # Add summary row
            if line_items:
                subtotal = sum(float(item.get('amount', '0') or '0') for item in line_items)
                tax_total = sum(float(item.get('tax_amount', '0') or '0') for item in line_items)
                grand_total = sum(float(item.get('total', '0') or '0') for item in line_items)
                
                summary_row = [
                    '',  # Invoice Number
                    '',  # Invoice Date
                    '',  # Vendor
                    '',  # Customer
                    '',  # Order Number
                    '',  # Tax ID
                    '',  # Line #
                    'TOTAL',  # Description
                    '',  # Quantity
                    '',  # Unit Price
                    f"{subtotal:.2f}",  # Amount
                    '',  # Tax Rate
                    f"{tax_total:.2f}",  # Tax Amount
                    f"{grand_total:.2f}"  # Total
                ]
                writer.writerow(summary_row)
        
        return output_file
    
    def _clean_number(self, value: str) -> str:
        """Clean and format number."""
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[£$€₹,\s]', '', value)
        # Keep only digits and decimal point
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        return cleaned if cleaned else ''
    
    def _clean_amount(self, value: str) -> str:
        """Clean and format monetary amount."""
        if not value:
            return ''
        # Remove currency symbols and common prefixes
        cleaned = re.sub(r'[£$€₹Rs\.rs\.,\s]', '', str(value))
        # Keep only digits and single decimal point
        # Handle cases like ".0.00" -> "0.00"
        if cleaned.startswith('.'):
            cleaned = '0' + cleaned
        # Remove extra decimal points (keep only first one)
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        # Keep digits and decimal point only
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        # Format as decimal
        try:
            if cleaned:
                return f"{float(cleaned):.2f}"
            return ''
        except (ValueError, TypeError):
            return ''
    
    def _clean_percentage(self, value: str) -> str:
        """Clean and format percentage."""
        cleaned = value.replace('%', '').strip()
        try:
            return f"{float(cleaned)}%" if cleaned else ''
        except:
            return value
    
    def _is_amount(self, value: str) -> bool:
        """Check if value looks like an amount."""
        if not value:
            return False
        # Remove currency symbols
        cleaned = re.sub(r'[£$€₹,\s]', '', value)
        # Check if it's a number
        try:
            float(cleaned)
            return True
        except:
            return False
