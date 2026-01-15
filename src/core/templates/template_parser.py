"""
Template Parser - Reads user-defined template configurations.

Templates are pure configuration, not code.
A template defines:
- Columns
- Mapping rules (JSONPath to canonical model)
- Optional transforms
- Row expansion rules (for line items)
"""
import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class TemplateParser:
    """
    Parses user-defined template configurations.
    
    Templates are JSON/YAML files that define how to map canonical model to output format.
    """
    
    def __init__(self):
        """Initialize template parser."""
        pass
    
    def parse_from_file(self, template_path: str) -> Dict[str, Any]:
        """
        Parse template from file.
        
        Args:
            template_path: Path to template JSON/YAML file
            
        Returns:
            Template configuration dictionary
        """
        path = Path(template_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() == '.json':
                return json.load(f)
            else:
                # Could add YAML support here
                raise ValueError(f"Unsupported template format: {path.suffix}")
    
    def parse_from_dict(self, template_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse template from dictionary.
        
        Args:
            template_dict: Template configuration dictionary
            
        Returns:
            Validated template configuration
        """
        return self._validate_template(template_dict)
    
    def parse_from_csv_headers(self, csv_headers: List[str]) -> Dict[str, Any]:
        """
        Parse template from CSV headers (auto-generate template).
        
        This allows users to upload a CSV template and auto-generate mappings.
        
        Args:
            csv_headers: List of CSV column headers
            
        Returns:
            Template configuration with auto-generated mappings
        """
        columns = []
        
        for header in csv_headers:
            # Auto-detect canonical path based on header name
            path = self._auto_detect_path(header)
            
            column_config = {
                "header": header,
                "path": path,
                "transform": None  # Can be enhanced with auto-detection
            }
            
            columns.append(column_config)
        
        return {
            "name": "Auto-generated from CSV",
            "columns": columns,
            "repeat": None  # No line item expansion by default
        }
    
    def _auto_detect_path(self, header: str) -> str:
        """
        Auto-detect canonical model path from CSV header.
        
        Args:
            header: CSV column header
            
        Returns:
            JSONPath to canonical model field
        """
        header_lower = header.lower().replace('_', ' ').replace('-', ' ')
        
        # Invoice fields
        if any(word in header_lower for word in ['invoice no', 'invoice number', 'invoice #']):
            return "invoice.invoice_number"
        elif any(word in header_lower for word in ['invoice date', 'date']):
            return "invoice.invoice_date"
        elif any(word in header_lower for word in ['due date']):
            return "invoice.due_date"
        elif any(word in header_lower for word in ['order', 'po', 'purchase order']):
            return "invoice.order_number"
        
        # Seller/Vendor fields
        elif any(word in header_lower for word in ['vendor', 'seller', 'supplier']):
            return "seller.name"
        elif any(word in header_lower for word in ['vendor tax', 'seller tax', 'gstin']):
            return "seller.tax_id"
        
        # Buyer/Customer fields
        elif any(word in header_lower for word in ['customer', 'buyer', 'bill to']):
            return "buyer.name"
        elif any(word in header_lower for word in ['customer tax', 'buyer tax']):
            return "buyer.tax_id"
        
        # Tax fields
        elif 'cgst' in header_lower:
            if 'rate' in header_lower:
                return "totals.cgst.rate"
            else:
                return "totals.cgst.amount"
        elif 'sgst' in header_lower:
            if 'rate' in header_lower:
                return "totals.sgst.rate"
            else:
                return "totals.sgst.amount"
        elif 'igst' in header_lower:
            if 'rate' in header_lower:
                return "totals.igst.rate"
            else:
                return "totals.igst.amount"
        elif any(word in header_lower for word in ['taxable', 'subtotal']):
            return "totals.taxable_value"
        elif any(word in header_lower for word in ['total', 'grand total']):
            return "totals.total"
        
        # Default: return header as-is (user will need to configure)
        return f"unknown.{header_lower.replace(' ', '_')}"
    
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
