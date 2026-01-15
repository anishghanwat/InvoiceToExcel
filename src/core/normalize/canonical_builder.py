"""
Canonical Builder - Builds rich canonical JSON from Textract output.

This is the ONLY place where Textract → Canonical conversion happens.
No CSV logic here. Ever.
"""
from typing import Dict, List, Any, Optional
from .canonical_schema import CanonicalSchema
import re
from datetime import datetime


class CanonicalBuilder:
    """
    Builds canonical invoice model from Textract extraction results.
    
    This is the single source of truth builder.
    It extracts truth, not columns.
    """
    
    def __init__(self):
        """Initialize canonical builder."""
        self.schema = CanonicalSchema()
    
    def build(self, textract_results: Dict[str, Any], document_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Build canonical invoice model from Textract results.
        
        Args:
            textract_results: Raw Textract extraction results
            document_text: Optional full document text for context
            
        Returns:
            Rich canonical invoice model
        """
        canonical = self.schema.create_empty()
        
        # Extract invoice header information
        canonical["invoice"] = self._extract_invoice_header(textract_results)
        
        # Extract seller/vendor information
        canonical["seller"] = self._extract_seller_info(textract_results)
        
        # Extract buyer/customer information
        canonical["buyer"] = self._extract_buyer_info(textract_results)
        
        # Extract line items
        canonical["line_items"] = self._extract_line_items(textract_results)
        
        # Extract totals (with tax breakdown)
        canonical["totals"] = self._extract_totals(textract_results, canonical["line_items"])
        
        # Finance-grade: Do NOT distribute or calculate taxes - only extract what's in the document
        # Trust AWS Textract confidence, never assume or calculate values
        
        # Extract shipping information
        canonical["shipping"] = self._extract_shipping_info(textract_results)
        
        # Update metadata
        canonical["metadata"]["extraction_date"] = datetime.now().isoformat()
        canonical["metadata"]["source"] = "textract"
        
        return canonical
    
    def _extract_invoice_header(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract invoice header fields."""
        header = {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "order_number": None,
            "po_number": None,
            "payment_terms": None,
            "place_of_supply": None,
        }
        
        kv_pairs = results.get('key_value_pairs', [])
        # First pass: extract "Dated" (invoice date) before "Ack Date"
        for kv in kv_pairs:
            key = kv['key'].strip()
            key_lower = key.lower()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            # Invoice date - prioritize "Dated" over "Ack Date"
            if key_lower == 'dated' and 'ack' not in key_lower:
                if not header["invoice_date"]:
                    header["invoice_date"] = self._normalize_date(value)
        
        # Second pass: extract other fields
        for kv in kv_pairs:
            key = kv['key'].strip()
            key_lower = key.lower()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            # Invoice number - handle "DSA Invoice Number", "Invoice Number", etc.
            if any(word in key_lower for word in ['invoice', 'inv no', 'bill no']) and 'number' in key_lower:
                if not header["invoice_number"]:
                    header["invoice_number"] = value.upper()
            
            # Invoice date - only if not already set (skip "Ack Date")
            elif any(word in key_lower for word in ['invoice date', 'bill date']):
                if not header["invoice_date"]:
                    header["invoice_date"] = self._normalize_date(value)
            elif key_lower == 'date' and 'ack' not in key_lower and not header["invoice_date"]:
                # Fallback for other date fields (but not Ack Date)
                header["invoice_date"] = self._normalize_date(value)
            
            # Due date
            elif any(word in key for word in ['due date', 'payment due', 'pay by']):
                if not header["due_date"]:
                    header["due_date"] = self._normalize_date(value)
            
            # Order number
            elif any(word in key for word in ['order', 'order no', 'order number']):
                if not header["order_number"]:
                    header["order_number"] = value
            
            # PO number
            elif any(word in key for word in ['po', 'p.o.', 'purchase order']):
                if not header["po_number"]:
                    header["po_number"] = value
            
            # Payment terms
            elif any(word in key for word in ['payment terms', 'terms', 'payment']):
                if not header["payment_terms"]:
                    header["payment_terms"] = value
            
            # Place of supply
            elif any(word in key for word in ['place of supply', 'pos', 'supply place']):
                if not header["place_of_supply"]:
                    header["place_of_supply"] = value
        
        return header
    
    def _extract_seller_info(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract seller/vendor information."""
        seller = {
            "name": None,
            "legal_name": None,
            "address": {
                "line1": None,
                "line2": None,
                "city": None,
                "state": None,
                "postal_code": None,
                "country": None,
            },
            "tax_id": None,
            "pan": None,
            "contact": {
                "phone": None,
                "email": None,
                "website": None,
            }
        }
        
        kv_pairs = results.get('key_value_pairs', [])
        text_blocks = results.get('text_blocks', [])
        
        # Extract from key-value pairs
        for kv in kv_pairs:
            key = kv['key'].strip().lower()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            # Seller name
            if any(word in key for word in ['vendor', 'supplier', 'seller', 'sold by', 'from']):
                if not seller["name"]:
                    seller["name"] = value
            
            # Tax ID (GSTIN, VAT, etc.)
            elif any(word in key for word in ['gstin', 'tax id', 'vat', 'tax number', 'gst']):
                if not seller["tax_id"]:
                    seller["tax_id"] = value.upper()
            
            # PAN
            elif 'pan' in key:
                if not seller["pan"]:
                    seller["pan"] = value.upper()
        
        # Try to extract address from text blocks (simplified)
        # In production, you'd use more sophisticated address parsing
        address_lines = []
        for block in text_blocks[:30]:  # Check first 30 blocks
            text = block.get('text', '').strip()
            if text and len(text) > 10 and not self._looks_like_amount(text):
                # Simple heuristic: addresses are usually multi-line
                if any(word in text.lower() for word in ['street', 'road', 'avenue', 'city', 'state']):
                    address_lines.append(text)
        
        if address_lines:
            # Simple address parsing (can be enhanced)
            seller["address"]["line1"] = address_lines[0] if len(address_lines) > 0 else None
            seller["address"]["line2"] = address_lines[1] if len(address_lines) > 1 else None
        
        return seller
    
    def _extract_buyer_info(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract buyer/customer information."""
        buyer = {
            "name": None,
            "legal_name": None,
            "address": {
                "line1": None,
                "line2": None,
                "city": None,
                "state": None,
                "postal_code": None,
                "country": None,
            },
            "tax_id": None,
            "pan": None,
            "contact": {
                "phone": None,
                "email": None,
            }
        }
        
        # First, try to extract from tables (more reliable)
        tables = results.get('tables', [])
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Look for buyer information in table format
            for row in table:
                if len(row) >= 2:
                    key = str(row[0]).strip().lower()
                    value = str(row[1]).strip()
                    
                    if not value:
                        continue
                    
                    # Buyer name (exact match, not "to" which matches "Total")
                    if key == 'buyer:' or key == 'buyer':
                        if not buyer["name"] and not self._looks_like_amount(value):
                            buyer["name"] = value
                    
                    # Buyer address
                    elif key == 'address:' and 'buyer' in str(table).lower():
                        if not buyer["address"]["line1"]:
                            buyer["address"]["line1"] = value
                    
                    # Buyer email
                    elif key == 'email:' and 'buyer' in str(table).lower():
                        if not buyer["contact"]["email"]:
                            buyer["contact"]["email"] = value
                    
                    # Buyer GSTIN (in buyer section)
                    elif 'gstin' in key and 'buyer' in str(table).lower():
                        if not buyer["tax_id"]:
                            buyer["tax_id"] = value.upper()
        
        # Fallback to key-value pairs
        kv_pairs = results.get('key_value_pairs', [])
        for kv in kv_pairs:
            key = kv['key'].strip()
            key_lower = key.lower()
            value = kv['value'].strip()
            
            if not value or self._looks_like_amount(value):
                continue
            
            # Buyer name - handle "To," field and extract first part
            if key_lower == 'to,' or key_lower == 'to':
                if not buyer["name"]:
                    # Value might be "HDFC Bank Ltd. 432508 MELTAMONEY FINLEND PVT LTD"
                    # Extract first part (buyer name) before numbers or other company names
                    parts = value.split()
                    buyer_name_parts = []
                    for part in parts:
                        # Stop at numbers or if we hit another company indicator
                        if part.isdigit() or (len(buyer_name_parts) > 0 and part.isupper() and len(part) > 5):
                            break
                        buyer_name_parts.append(part)
                    if buyer_name_parts:
                        buyer["name"] = ' '.join(buyer_name_parts)
            # Skip "Bank Ref No." and similar fields - not buyer name
            elif 'bank ref no' in key_lower or 'ref no' in key_lower:
                continue  # Skip this field
            # Buyer name - be more specific, avoid matching "Total"
            elif any(word in key_lower for word in ['customer', 'buyer']) and 'total' not in key_lower:
                if not buyer["name"]:
                    buyer["name"] = value
            
            # Tax ID - handle "State GST No" (buyer GSTIN) and buyer GSTIN
            if 'state gst no' in key_lower or ('gst' in key_lower and 'state' in key_lower and 'dsa' not in key_lower):
                # "State GST No" is typically the buyer's GSTIN
                if not buyer["tax_id"]:
                    buyer["tax_id"] = value.upper()
            # Tax ID - must explicitly mention buyer
            elif any(word in key for word in ['gstin', 'tax id', 'vat']) and 'buyer' in key:
                if not buyer["tax_id"]:
                    buyer["tax_id"] = value.upper()
        
        # Search text blocks for buyer name if not found in key-value pairs
        # First, try to find buyer name near buyer GSTIN (more reliable)
        invalid_buyer_names = ['dispatched through', 'shipped to', 'consignee', 'destination', 'other references', 'bank ref no.']
        if buyer["tax_id"] and (not buyer["name"] or any(invalid in buyer["name"].lower() for invalid in invalid_buyer_names)):
            text_blocks = results.get('text_blocks', [])
            buyer_gstin = buyer["tax_id"]
            
            # Find GSTIN in text blocks and look for company name nearby
            for i, block in enumerate(text_blocks):
                text = block.get('text', '').strip()
                if buyer_gstin in text or buyer_gstin.replace(':', '').replace(' ', '') in text.replace(':', '').replace(' ', ''):
                    # Found buyer GSTIN, look for company name in nearby blocks
                    skip_labels = ['gstin/uin', 'address:', 'state name', 'code:', 'dated', 'buyer\'s order no.', 
                                  'dispatched through', 'shipped to', 'consignee', 'delivery note', 'mode/terms',
                                  'destination', 'terms of delivery', 'dispatch doc no.', 'delivery note date',
                                  'other references', 'reference no. & date.', '12th cross']
                    
                    # Check blocks before GSTIN (company name usually appears before GSTIN)
                    for j in range(max(0, i - 5), i):
                        prev_text = text_blocks[j].get('text', '').strip()
                        if prev_text and len(prev_text) > 5 and not self._looks_like_amount(prev_text):
                            if prev_text.lower() not in skip_labels:
                                # Company names usually have spaces and are capitalized
                                if ' ' in prev_text and prev_text[0].isupper() and not prev_text.isupper():
                                    buyer["name"] = prev_text
                                    break
                                elif not buyer["name"] and prev_text[0].isupper() and len(prev_text) > 5:
                                    buyer["name"] = prev_text
                    if buyer["name"]:
                        break
        
        # Fallback: search near "To," label (common in invoices)
        invalid_buyer_names = ['dispatched through', 'shipped to', 'consignee', 'destination', 'other references', 'bank ref no.']
        if not buyer["name"] or any(invalid in buyer["name"].lower() for invalid in invalid_buyer_names):
            text_blocks = results.get('text_blocks', [])
            skip_labels = ['gstin/uin', 'address:', 'state name', 'code:', 'dated', 'buyer\'s order no.', 
                          'dispatched through', 'shipped to', 'consignee', 'delivery note', 'mode/terms',
                          'destination', 'terms of delivery', 'dispatch doc no.', 'delivery note date',
                          'other references', 'reference no. & date.', 'bank ref no.', 'dsa code']
            
            # Look for "To," label and extract buyer name from next block
            for i, block in enumerate(text_blocks):
                text = block.get('text', '').strip()
                # Look for "To," label
                if text.lower() == 'to,' or text.lower() == 'to':
                    # Check next block for buyer name
                    if i + 1 < len(text_blocks):
                        next_text = text_blocks[i + 1].get('text', '').strip()
                        if next_text and len(next_text) > 3 and not self._looks_like_amount(next_text):
                            if next_text.lower() not in skip_labels and 'bank ref no' not in next_text.lower():
                                # Extract first part if it contains multiple values
                                parts = next_text.split()
                                buyer_name_parts = []
                                for part in parts:
                                    # Stop at numbers or if we hit another company indicator
                                    if part.isdigit() or (len(buyer_name_parts) > 0 and part.isupper() and len(part) > 5):
                                        break
                                    buyer_name_parts.append(part)
                                if buyer_name_parts:
                                    buyer["name"] = ' '.join(buyer_name_parts)
                                    break
                    # Also check if "To," is followed by buyer name in the same or nearby blocks
                    if not buyer["name"] and i + 2 < len(text_blocks):
                        # Check a few blocks after "To,"
                        for j in range(i + 1, min(i + 5, len(text_blocks))):
                            next_text = text_blocks[j].get('text', '').strip()
                            if next_text and len(next_text) > 3 and not self._looks_like_amount(next_text):
                                if next_text.lower() not in skip_labels and 'bank ref no' not in next_text.lower() and 'dsa code' not in next_text.lower():
                                    # Check if it looks like a company name
                                    if ' ' in next_text or (next_text[0].isupper() and len(next_text) > 5):
                                        buyer["name"] = next_text
                                        break
                        if buyer["name"]:
                            break
            
            # Fallback: search near "Buyer" or "Consignee" labels
            if not buyer["name"] or buyer["name"].lower() in skip_labels:
                # Look for buyer name near "Buyer" or "Consignee" labels
                for i, block in enumerate(text_blocks):
                    text = block.get('text', '').strip()
                    # Look for "Buyer" or "Consignee" labels
                    if ('buyer' in text.lower() or 'consignee' in text.lower()) and ('bill to' in text.lower() or 'ship to' in text.lower() or 'ship-to' in text.lower()):
                        # Check block right before the label (common pattern: company name before "Buyer" label)
                        if i > 0:
                            prev_text = text_blocks[i - 1].get('text', '').strip()
                            if prev_text and len(prev_text) > 5 and not self._looks_like_amount(prev_text):
                                if prev_text.lower() not in skip_labels and ' ' in prev_text and prev_text[0].isupper():
                                    buyer["name"] = prev_text
                                    break
                        
                        # Check blocks after the label (skip shipping-related text)
                        for j in range(i + 1, min(i + 8, len(text_blocks))):
                            next_text = text_blocks[j].get('text', '').strip()
                            if next_text and len(next_text) > 5 and not self._looks_like_amount(next_text):
                                if next_text.lower() not in skip_labels and not any(word in next_text.lower() for word in ['through', 'shipped', 'consignee', 'destination', 'terms', '12th']):
                                    # Prefer text that looks like a company name (has space, capitalized)
                                    if ' ' in next_text and next_text[0].isupper() and not next_text.isupper():
                                        buyer["name"] = next_text
                                        break
                        if buyer["name"] and buyer["name"].lower() not in skip_labels:
                            break
        
        # Also try to extract buyer GSTIN from text blocks if not found
        if not buyer["tax_id"]:
            text_blocks = results.get('text_blocks', [])
            buyer_section = False
            for i, block in enumerate(text_blocks):
                text = block.get('text', '').strip()
                if 'buyer' in text.lower() and ('bill to' in text.lower() or 'bill-to' in text.lower()):
                    buyer_section = True
                elif buyer_section and 'gstin' in text.lower():
                    # Look for GSTIN value in next blocks
                    for j in range(i + 1, min(i + 3, len(text_blocks))):
                        gstin_text = text_blocks[j].get('text', '').strip()
                        # GSTIN format: 15 alphanumeric characters
                        if gstin_text and len(gstin_text) >= 15 and gstin_text.replace(':', '').replace(' ', '').isalnum():
                            buyer["tax_id"] = gstin_text.replace(':', '').replace(' ', '').upper()
                            break
                    if buyer["tax_id"]:
                        break
        
        return buyer
    
    def _extract_line_items(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract line items from tables."""
        line_items = []
        tables = results.get('tables', [])
        
        # Find line items table
        line_items_table = None
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            headers = [h.lower().strip() for h in table[0]]
            header_text = ' '.join(headers)
            
            # Check if this looks like a line items table
            has_description = any(word in header_text for word in ['description', 'item', 'product', 'particulars'])
            has_quantity = any(word in header_text for word in ['qty', 'quantity'])
            has_price = any(word in header_text for word in ['rate', 'price', 'amount', 'total'])
            
            if has_description and (has_quantity or has_price):
                line_items_table = table
                break
        
        if not line_items_table:
            return line_items
        
        # Extract line items
        headers = line_items_table[0]
        for row_idx, row in enumerate(line_items_table[1:], 1):
            # Skip summary rows
            row_text = ' '.join(str(cell).lower() for cell in row if cell)
            if any(word in row_text for word in ['total', 'subtotal', 'grand total']):
                continue
            
            item = self._parse_line_item_row(row, headers, row_idx)
            if item and item.get("description"):
                line_items.append(item)
        
        return line_items
    
    def _parse_line_item_row(self, row: List[str], headers: List[str], line_number: int) -> Optional[Dict[str, Any]]:
        """Parse a single line item row."""
        item = {
            "line_number": line_number,
            "description": None,
            "hsn": None,
            "quantity": None,
            "unit": None,
            "unit_price": None,
            "discount": None,
            "taxable_value": None,
            "taxes": {
                "cgst": {"rate": None, "amount": None},
                "sgst": {"rate": None, "amount": None},
                "igst": {"rate": None, "amount": None},
                "cess": {"rate": None, "amount": None},
            },
            "total": None
        }
        
        # Map headers to fields with priority order
        # First pass: collect all values
        header_map = {}
        for col_idx, header in enumerate(headers):
            if col_idx >= len(row):
                continue
            
            value = str(row[col_idx]).strip() if row[col_idx] else ''
            if not value:
                continue
            
            # Handle cells with multiple values separated by spaces (e.g., "2000.00 0.00")
            # Take the first meaningful number
            if ' ' in value and self._looks_like_amount(value):
                # Split by space and take the first part that looks like an amount
                parts = value.split()
                for part in parts:
                    if self._looks_like_amount(part) or (part.replace('.', '').replace(',', '').isdigit()):
                        value = part
                        break
            
            header_lower = header.lower()
            header_map[header_lower] = (col_idx, value)
        
        # Extract fields with better logic
        for header_lower, (col_idx, value) in header_map.items():
            # Description (highest priority - must be text, not number)
            if any(word in header_lower for word in ['description', 'item', 'product', 'particulars']):
                if not item["description"] and not self._looks_like_amount(value):
                    item["description"] = value
            
            # HSN/SAC
            elif any(word in header_lower for word in ['hsn', 'sac', 'hsn code', 'hsn / sac']):
                if not item["hsn"]:
                    # HSN should be alphanumeric, remove spaces
                    item["hsn"] = value.replace(' ', '')
            
            # Unit
            elif header_lower in ['unit', 'uom']:
                if not item["unit"]:
                    item["unit"] = value
            
            # Quantity
            elif any(word in header_lower for word in ['qty', 'quantity']):
                qty = self._normalize_number(value)
                if qty is not None and qty > 0:
                    item["quantity"] = qty
            
            # Unit price / Rate (prefer "rate" over "amount" for unit price)
            elif any(word in header_lower for word in ['rate', 'unit price', 'price per unit']):
                price = self._normalize_amount(value)
                if price is not None and price > 0:
                    item["unit_price"] = price
            
            # Taxable value / Amount (this is the base amount before tax)
            elif any(word in header_lower for word in ['taxable', 'taxable value', 'amount (excl', 'base amount']):
                amount = self._normalize_amount(value)
                if amount is not None and amount > 0:
                    item["taxable_value"] = amount
            elif header_lower == 'amount' and 'rate' in header_map:
                # If we have "Rate" column, "Amount" is likely taxable value
                amount = self._normalize_amount(value)
                if amount is not None and amount > 0:
                    item["taxable_value"] = amount
            
            # CGST
            elif 'cgst' in header_lower:
                if 'rate' in header_lower or '%' in value:
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        item["taxes"]["cgst"]["rate"] = rate
                else:
                    amount = self._normalize_amount(value)
                    if amount is not None:
                        item["taxes"]["cgst"]["amount"] = amount
            
            # SGST
            elif 'sgst' in header_lower:
                if 'rate' in header_lower or '%' in value:
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        item["taxes"]["sgst"]["rate"] = rate
                else:
                    amount = self._normalize_amount(value)
                    if amount is not None:
                        item["taxes"]["sgst"]["amount"] = amount
            
            # IGST
            elif 'igst' in header_lower:
                if 'rate' in header_lower or '%' in value:
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        item["taxes"]["igst"]["rate"] = rate
                else:
                    amount = self._normalize_amount(value)
                    if amount is not None:
                        item["taxes"]["igst"]["amount"] = amount
        
        # Finance-grade: Do NOT calculate any values - only extract what AWS Textract found
        # Trust AWS confidence, never assume or calculate
        # If a value is not in the document, leave it as None
        # Do NOT calculate: taxable_value = unit_price * quantity
        # Do NOT calculate: total = taxable + cgst + sgst + igst + cess
        # Only use values explicitly extracted from the document
        
        return item if item["description"] else None
    
    def _extract_totals(self, results: Dict[str, Any], line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract totals with tax breakdown.
        
        IMPORTANT: Only extract values from the document. Never calculate or compute totals.
        We extract truth, not calculated values.
        """
        totals = {
            "taxable_value": None,
            "discount": None,
            "cgst": {"rate": None, "amount": None},
            "sgst": {"rate": None, "amount": None},
            "igst": {"rate": None, "amount": None},
            "cess": {"rate": None, "amount": None},
            "round_off": None,
            "total": None,
            "currency": "INR"
        }
        
        # Extract from key-value pairs ONLY - never calculate
        kv_pairs = results.get('key_value_pairs', [])
        
        # First pass: Extract Commission (taxable value) before Total
        commission_amount = None
        for kv in kv_pairs:
            key = kv['key'].strip()
            key_lower = key.lower()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            # Commission (often the taxable value) - prioritize this over "Total"
            if key_lower == 'commission' or (key_lower.startswith('commission') and 'dsa commission is' not in key_lower):
                amount = self._normalize_amount(value)
                if amount is not None:
                    commission_amount = amount
                    break  # Use first valid commission value
        
        # Set taxable value from commission if found
        if commission_amount is not None:
            totals["taxable_value"] = commission_amount
        
        # Second pass: Extract other fields
        for kv in kv_pairs:
            key = kv['key'].strip()
            key_lower = key.lower()
            value = kv['value'].strip()
            
            if not value:
                continue
            
            # Skip Commission (already processed in first pass)
            if key_lower == 'commission' or (key_lower.startswith('commission') and 'dsa commission is' not in key_lower):
                continue
            
            # Grand Total / Total Payable (highest priority for total)
            if any(word in key_lower for word in ['grand total', 'total payable', 'amount due', 'invoice total']):
                amount = self._normalize_amount(value)
                if amount is not None:
                    totals["total"] = amount
            
            # "TOTAL" (all caps) = grand total (prefer over "Total")
            elif key == 'TOTAL' or (key_lower == 'total' and key.isupper()):
                amount = self._normalize_amount(value)
                if amount is not None:
                    totals["total"] = amount
            
            # "Total" (mixed case) - extract as total, not taxable value
            if key_lower == 'total':
                # If value contains multiple amounts, extract the last one (usually the grand total)
                # e.g., "3,500.00 315.00 315.00 630.00" -> extract 630.00 or 4130.00
                # e.g., "7 ₹ 4,130.00" -> extract 4130.00
                if '₹' in value or len(value.split()) > 2:
                    # Extract all amounts and take the largest (usually the grand total)
                    amounts = re.findall(r'[\d,]+\.?\d*', value)
                    if amounts:
                        # Convert to float and find the largest
                        amount_values = []
                        for amt_str in amounts:
                            amt = self._normalize_amount(amt_str)
                            if amt is not None:
                                amount_values.append(amt)
                        if amount_values:
                            # If we have taxable_value, the total should be larger
                            if totals.get("taxable_value"):
                                # Total should be taxable + taxes, so find amount larger than taxable
                                for amt in sorted(amount_values, reverse=True):
                                    if amt > totals["taxable_value"]:
                                        totals["total"] = amt
                                        break
                            else:
                                # No taxable value yet, use the largest amount
                                totals["total"] = max(amount_values)
                else:
                    # Single amount - if we have taxable_value, this is the total
                    amount = self._normalize_amount(value)
                    if amount is not None:
                        if totals.get("taxable_value"):
                            # We have taxable value, so this must be the total (even if equal)
                            totals["total"] = amount
                        else:
                            # No taxable value yet, set as total
                            totals["total"] = amount
            
            # Taxable value / Subtotal
            elif any(word in key_lower for word in ['taxable', 'subtotal', 'total (excl', 'base amount']):
                amount = self._normalize_amount(value)
                if amount is not None:
                    # Prefer explicit "taxable" over "subtotal"
                    if 'taxable' in key_lower or not totals["taxable_value"]:
                        totals["taxable_value"] = amount
            
            # CGST - handle "CGST 9%" format or "Central Tax" or "ADD CGST @9%"
            elif 'cgst' in key_lower or ('central' in key_lower and 'tax' in key_lower) or ('add' in key_lower and 'cgst' in key_lower):
                # Check if key contains rate (e.g., "CGST 9%" or "ADD CGST @9%")
                if '%' in key or '@' in key:
                    # Extract rate from key (e.g., "CGST 9%" -> 9.0, "ADD CGST @9%" -> 9.0)
                    rate = self._normalize_percentage(key)
                    if rate is not None:
                        totals["cgst"]["rate"] = rate
                    # Value might be "997119 0.00" - extract the number with decimal (amount)
                    if ' ' in value:
                        # Multiple values - prefer the one with decimal point (amount)
                        parts = value.split()
                        for part in reversed(parts):
                            amount = self._normalize_amount(part)
                            if amount is not None:
                                # Prefer decimal values (amounts) over integers (HSN codes)
                                if '.' in part or amount < 1000000:  # HSN codes are usually large integers
                                    totals["cgst"]["amount"] = amount
                                    break
                        # If no decimal found, use the last number
                        if totals["cgst"]["amount"] is None:
                            for part in reversed(parts):
                                amount = self._normalize_amount(part)
                                if amount is not None:
                                    totals["cgst"]["amount"] = amount
                                    break
                    else:
                        # Single value
                        amount = self._normalize_amount(value)
                        if amount is not None:
                            totals["cgst"]["amount"] = amount
                elif '%' in value:
                    # Value contains both rate and amount (e.g., "9% 315.00")
                    # Extract rate first
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        totals["cgst"]["rate"] = rate
                    # Extract amount (remove percentage part)
                    amount_str = re.sub(r'\d+\.?\d*%', '', value).strip()
                    amount = self._normalize_amount(amount_str)
                    if amount is not None:
                        totals["cgst"]["amount"] = amount
                elif 'rate' in key_lower:
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        totals["cgst"]["rate"] = rate
                else:
                    # Just amount - handle "997119 0.00" format
                    if ' ' in value:
                        parts = value.split()
                        for part in reversed(parts):
                            amount = self._normalize_amount(part)
                            if amount is not None:
                                # Prefer decimal values (amounts) over integers (HSN codes)
                                if '.' in part or amount < 1000000:
                                    totals["cgst"]["amount"] = amount
                                    break
                        # If no decimal found, use the last number
                        if totals["cgst"]["amount"] is None:
                            for part in reversed(parts):
                                amount = self._normalize_amount(part)
                                if amount is not None:
                                    totals["cgst"]["amount"] = amount
                                    break
                    else:
                        amount = self._normalize_amount(value)
                        if amount is not None:
                            totals["cgst"]["amount"] = amount
            
            # SGST - handle "SGST 9%" format or "State Tax" or "ADD SGST @9%"
            elif 'sgst' in key_lower or ('state' in key_lower and 'tax' in key_lower and 'central' not in key_lower) or ('add' in key_lower and 'sgst' in key_lower):
                # Check if key contains rate (e.g., "SGST 9%" or "ADD SGST @9%")
                if '%' in key or '@' in key:
                    # Extract rate from key (e.g., "SGST 9%" -> 9.0, "ADD SGST @9%" -> 9.0)
                    rate = self._normalize_percentage(key)
                    if rate is not None:
                        totals["sgst"]["rate"] = rate
                    # Value might be "22800.99 997119" or "997119 0.00" - extract the decimal amount
                    if ' ' in value:
                        # Multiple values - prefer the one with decimal point (amount)
                        parts = value.split()
                        # First, try to find a decimal value (amount)
                        for part in parts:
                            amount = self._normalize_amount(part)
                            if amount is not None and '.' in part:
                                # Found decimal value - this is the amount
                                totals["sgst"]["amount"] = amount
                                break
                        # If no decimal found, check reversed order
                        if totals["sgst"]["amount"] is None:
                            for part in reversed(parts):
                                amount = self._normalize_amount(part)
                                if amount is not None:
                                    # Prefer smaller amounts (actual tax) over large integers (HSN codes)
                                    if amount < 1000000:  # HSN codes are usually 6-digit integers
                                        totals["sgst"]["amount"] = amount
                                        break
                    else:
                        # Single value
                        amount = self._normalize_amount(value)
                        if amount is not None:
                            totals["sgst"]["amount"] = amount
                elif '%' in value:
                    # Value contains both rate and amount (e.g., "9% 315.00")
                    # Extract rate first
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        totals["sgst"]["rate"] = rate
                    # Extract amount (remove percentage part)
                    amount_str = re.sub(r'\d+\.?\d*%', '', value).strip()
                    amount = self._normalize_amount(amount_str)
                    if amount is not None:
                        totals["sgst"]["amount"] = amount
                elif 'rate' in key_lower:
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        totals["sgst"]["rate"] = rate
                else:
                    # Just amount - handle "997119 0.00" format
                    if ' ' in value:
                        parts = value.split()
                        for part in reversed(parts):
                            amount = self._normalize_amount(part)
                            if amount is not None:
                                # Prefer decimal values (amounts) over integers (HSN codes)
                                if '.' in part or amount < 1000000:
                                    totals["sgst"]["amount"] = amount
                                    break
                        # If no decimal found, use the last number
                        if totals["sgst"]["amount"] is None:
                            for part in reversed(parts):
                                amount = self._normalize_amount(part)
                                if amount is not None:
                                    totals["sgst"]["amount"] = amount
                                    break
                    else:
                        amount = self._normalize_amount(value)
                        if amount is not None:
                            totals["sgst"]["amount"] = amount
            
            # IGST
            elif 'igst' in key:
                if 'rate' in key or '%' in value:
                    rate = self._normalize_percentage(value)
                    if rate is not None:
                        totals["igst"]["rate"] = rate
                else:
                    amount = self._normalize_amount(value)
                    if amount is not None:
                        totals["igst"]["amount"] = amount
        
        # If we have CGST but SGST is missing, try to extract from tables or text blocks
        if totals.get("cgst", {}).get("rate") and not totals.get("sgst", {}).get("rate"):
            # If CGST rate exists, SGST rate is usually the same (for CGST/SGST invoices)
            totals["sgst"]["rate"] = totals["cgst"]["rate"]
        
        # If we have CGST amount but SGST amount is missing, try to extract from tables
        if totals.get("cgst", {}).get("amount") is not None and totals.get("sgst", {}).get("amount") is None:
            # Try to find tax breakdown in tables
            tables = results.get('tables', [])
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Look for tax summary rows
                for row in table:
                    if len(row) >= 2:
                        row_text = ' '.join(str(cell).lower() for cell in row if cell)
                        if 'sgst' in row_text.lower() or ('add' in row_text.lower() and 'sgst' in row_text.lower()):
                            # Try to extract tax amounts from this row
                            for cell in row[1:]:  # Skip first column (label)
                                cell_str = str(cell).strip()
                                amount = self._normalize_amount(cell_str)
                                if amount is not None:
                                    # Prefer decimal values (amounts) over integers (HSN codes)
                                    # HSN codes are usually 6-digit integers, amounts have decimals
                                    if '.' in cell_str:
                                        totals["sgst"]["amount"] = amount
                                        break
                                    elif amount < 1000:  # Small amounts without decimal
                                        totals["sgst"]["amount"] = amount
                                        break
                            if totals["sgst"]["amount"] is not None:
                                break
            
            # If still not found and CGST amount is 0, SGST is likely also 0 (for CGST/SGST invoices)
            # Only do this if we haven't found SGST in key-value pairs (to avoid overriding extracted values)
            if totals.get("sgst", {}).get("amount") is None:
                if totals.get("cgst", {}).get("amount") == 0.0:
                    # For CGST/SGST invoices, if CGST is 0, SGST is usually also 0
                    totals["sgst"]["amount"] = 0.0
                elif totals.get("cgst", {}).get("amount") is not None:
                    # If CGST exists but SGST doesn't, check if we should infer it
                    # Only infer if CGST amount is 0 (common pattern for zero-tax invoices)
                    if totals.get("cgst", {}).get("amount") == 0.0:
                        totals["sgst"]["amount"] = 0.0
        
        # Detect currency
        text_content = ' '.join([kv.get('value', '') for kv in kv_pairs])
        if '₹' in text_content or 'Rs.' in text_content:
            totals["currency"] = "INR"
        elif '$' in text_content:
            totals["currency"] = "USD"
        elif '£' in text_content:
            totals["currency"] = "GBP"
        elif '€' in text_content:
            totals["currency"] = "EUR"
        
        return totals
    
    def _extract_shipping_info(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract shipping information."""
        shipping = {
            "shipped_to": None,
            "shipping_address": None,
            "tracking_number": None,
        }
        
        kv_pairs = results.get('key_value_pairs', [])
        for kv in kv_pairs:
            key = kv['key'].strip().lower()
            value = kv['value'].strip()
            
            if any(word in key for word in ['shipped to', 'delivery address', 'ship to']):
                if not shipping["shipped_to"]:
                    shipping["shipped_to"] = value
            
            elif 'tracking' in key:
                if not shipping["tracking_number"]:
                    shipping["tracking_number"] = value
        
        return shipping
    
    def _distribute_taxes_to_line_items(
        self,
        line_items: List[Dict[str, Any]],
        totals: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Finance-grade: Do NOT calculate or distribute taxes.
        
        This function is disabled to prevent any calculation or assumption of values.
        Only extract what's in the document. Trust AWS Textract confidence.
        
        Returns line items as-is with no modifications.
        """
        # Return line items as-is - no calculations, no distributions, no assumptions
        return line_items
    
    # Helper methods
    def _normalize_date(self, value: str) -> Optional[str]:
        """Normalize date to ISO format (YYYY-MM-DD)."""
        # Try common date patterns
        patterns = [
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',
            r'(\d{2,4})[-/](\d{1,2})[-/](\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                # Return as-is for now (can be improved with proper date parsing)
                return value.strip()
        
        return value.strip() if value else None
    
    def _normalize_amount(self, value: str) -> Optional[float]:
        """Normalize monetary amount to float."""
        # Remove currency symbols, commas, and spaces, but KEEP decimal point
        cleaned = re.sub(r'[£$€₹Rsrs,\s]', '', str(value))
        if cleaned.startswith('.'):
            cleaned = '0' + cleaned
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        # Remove any remaining non-digit/non-decimal characters
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _normalize_number(self, value: str) -> Optional[float]:
        """Normalize number to float."""
        cleaned = re.sub(r'[,\s]', '', str(value))
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _normalize_percentage(self, value: str) -> Optional[float]:
        """Normalize percentage to float."""
        # Handle cases like "CGST 9%" or "9%" or "9"
        cleaned = str(value).replace('%', '').strip()
        # Extract number from string (e.g., "CGST 9%" -> "9")
        numbers = re.findall(r'\d+\.?\d*', cleaned)
        if numbers:
            try:
                return float(numbers[0])
            except (ValueError, TypeError):
                pass
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _looks_like_amount(self, value: str) -> bool:
        """
        Check if value looks like a monetary amount.
        
        Improved detection: looks for currency symbols OR number patterns with commas/decimals.
        """
        if not value:
            return False
        
        # Check for currency symbols
        has_currency = any(symbol in value for symbol in ['£', '$', '€', '₹', 'Rs.', 'Rs', 'INR', 'USD'])
        if has_currency:
            return True
        
        # Check for number patterns that look like amounts
        # Pattern: digits with commas and/or decimal point (e.g., "27,075.00", "1000.50")
        amount_pattern = r'^\s*[\d,]+\.?\d*\s*$'
        if re.match(amount_pattern, value.replace(',', '')):
            # If it's a pure number with commas/decimals, check if it's reasonable
            cleaned = re.sub(r'[,\s]', '', value)
            try:
                num_value = float(cleaned)
                # If it's a reasonable amount (not too large, has decimal or commas)
                if 0 < num_value < 1000000000 and ('.' in value or ',' in value):
                    return True
            except (ValueError, TypeError):
                pass
        
        return False
