"""
Template Exporter - Applies template mappings to canonical model.

This is where flexibility happens. Templates are pure configuration.
No AI needed here. Deterministic. Fast. User-controllable.
"""
import csv
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from .template_parser import TemplateParser


class TemplateExporter:
    """
    Exports canonical invoice model to CSV/Excel using template configuration.
    
    This is the template engine. It:
    - Reads template configuration
    - Maps canonical model fields to output columns
    - Applies transforms
    - Handles row expansion (line items)
    - Generates output files
    """
    
    def __init__(self):
        """Initialize template exporter."""
        self.parser = TemplateParser()
    
    def export_to_csv(
        self,
        canonical: Dict[str, Any],
        template: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Export canonical model to CSV using template.
        
        Args:
            canonical: Canonical invoice model
            template: Template configuration
            output_path: Output CSV file path
            
        Returns:
            Path to created CSV file
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Check if template has row expansion (line items)
        if template.get("repeat") == "line_items":
            return self._export_line_items_csv(canonical, template, output_path)
        else:
            return self._export_single_row_csv(canonical, template, output_path)
    
    def export_mapped_data_to_csv(
        self,
        mapped_data: Dict[str, Any],
        template: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Export pre-mapped data to CSV (from Dynamic Mapper).
        
        Args:
            mapped_data: Pre-mapped data {column_name: value}
            template: Template configuration
            output_path: Output CSV file path
        
        Returns:
            Path to created CSV file
        """
        print("📊 [EXPORTER] Starting CSV export with mapped data...")
        print(f"📊 [EXPORTER] Mapped data keys: {list(mapped_data.keys())}")
        print(f"📊 [EXPORTER] Mapped data values: {mapped_data}")
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        columns = template.get("columns", [])
        print(f"📊 [EXPORTER] Template has {len(columns)} columns")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write headers
            headers = [col.get("header", "") for col in columns]
            print(f"📊 [EXPORTER] Writing headers: {headers}")
            writer.writerow(headers)
            
            # Write data row
            row = []
            for col in columns:
                header = col.get("header", "")
                value = mapped_data.get(header)
                
                print(f"📊 [EXPORTER] Column '{header}': value = {value} (type: {type(value).__name__})")
                
                # Format value
                if value is None:
                    value = ""
                    print(f"📊 [EXPORTER] Column '{header}': converted None to empty string")
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value, default=str)
                    print(f"📊 [EXPORTER] Column '{header}': converted {type(value).__name__} to JSON string")
                else:
                    value = str(value)
                    print(f"📊 [EXPORTER] Column '{header}': converted to string: '{value}'")
                
                row.append(value)
            
            print(f"📊 [EXPORTER] Writing row: {row}")
            writer.writerow(row)
        
        print(f"✅ [EXPORTER] CSV exported to: {output_path}")
        return output_path
    
    def _export_single_row_csv(
        self,
        canonical: Dict[str, Any],
        template: Dict[str, Any],
        output_path: str
    ) -> str:
        """Export single row (invoice-level) CSV."""
        columns = template.get("columns", [])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write headers
            headers = [col["header"] for col in columns]
            writer.writerow(headers)
            
            # Write data row
            row = []
            for col in columns:
                # Check for static value first
                if "static_value" in col:
                    value = col["static_value"]
                else:
                    path = col.get("path")
                    if path is None:
                        value = ""
                    else:
                        value = self._get_value_from_path(canonical, path)
                    
                    # No hardcoded field aliases - AI should handle mapping correctly
                    # If value is None, it means the path doesn't exist in canonical
                    
                    # Handle dict values - AI should map to correct structure
                    # If value is a dict, it means the path points to an object
                    # Convert to string representation (AI should have mapped to the correct field)
                    if isinstance(value, dict):
                        # Try common invoice data fields
                        if "amount" in value:
                            value = value["amount"]
                        elif "value" in value:
                            value = value["value"]
                        else:
                            # Convert dict to string representation
                            value = str(value)
                    
                    # Apply transform if specified
                    if col.get("transform"):
                        value = self._apply_transform(value, col["transform"])
                    elif value is None:
                        value = ""
                
                # Ensure value is string
                if not isinstance(value, str):
                    value = str(value) if value is not None else ""
                
                row.append(value)
            
            writer.writerow(row)
        
        return output_path
    
    def _export_line_items_csv(
        self,
        canonical: Dict[str, Any],
        template: Dict[str, Any],
        output_path: str
    ) -> str:
        """Export line items CSV (one row per line item)."""
        columns = template.get("columns", [])
        line_items = canonical.get("line_items", [])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write headers
            headers = [col["header"] for col in columns]
            writer.writerow(headers)
            
            # Write line items
            for item in line_items:
                row = []
                
                for col in columns:
                    # Check for static value first
                    if "static_value" in col:
                        value = col["static_value"]
                    else:
                        path = col.get("path")
                        if path is None:
                            value = ""
                        else:
                            # Check if path starts with invoice/seller/buyer/totals (invoice-level)
                            if path.startswith("invoice.") or path.startswith("seller.") or \
                               path.startswith("buyer.") or path.startswith("totals."):
                                # Get from canonical root
                                value = self._get_value_from_path(canonical, path)
                            else:
                                # Get from line item first
                                value = self._get_value_from_path(item, path)
                                
                                # Finance-grade: If line item doesn't have tax/total values, fall back to totals
                                # This ensures extracted totals appear even when line items don't have individual values
                                if value is None:
                                    if path.startswith("taxes."):
                                        # Map taxes.cgst.amount -> totals.cgst.amount
                                        totals_path = "totals." + path.replace("taxes.", "")
                                        value = self._get_value_from_path(canonical, totals_path)
                                    elif path == "total":
                                        # Map total -> totals.total
                                        value = self._get_value_from_path(canonical, "totals.total")
                        
                        # Apply transform if specified
                        if col.get("transform"):
                            value = self._apply_transform(value, col["transform"])
                        elif value is None:
                            value = ""
                    
                    # Ensure value is properly formatted string (avoid #### in Excel)
                    if value is None:
                        value = ""
                    elif isinstance(value, dict):
                        # If value is a dict, try to extract a meaningful value
                        # Common cases: tax objects with amount/rate, address objects
                        if "amount" in value:
                            value = value["amount"]
                        elif "rate" in value:
                            value = value["rate"]
                        elif "value" in value:
                            value = value["value"]
                        else:
                            # Convert dict to string representation
                            value = str(value)
                    elif isinstance(value, (int, float)):
                        # Format numbers without commas to avoid Excel issues
                        value = str(value)
                    elif isinstance(value, list):
                        # If it's a list, join or take first element
                        if value:
                            value = str(value[0]) if not isinstance(value[0], dict) else str(value)
                        else:
                            value = ""
                    else:
                        value = str(value)
                    
                    row.append(value)
                
                writer.writerow(row)
        
        return output_path
    
    def _get_value_from_path(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get value from canonical model using JSONPath-like syntax.
        
        Args:
            data: Dictionary to extract from
            path: JSONPath (e.g., "invoice.invoice_number", "totals.cgst.amount", "line_items[].rate")
            
        Returns:
            Extracted value or None
        """
        # Handle static values
        if path == "static":
            return None  # Will be handled by static_value in column config
        
        # Handle array notation (e.g., "line_items[].rate")
        if "[].]" in path or path.endswith("[]"):
            # For single-row exports, get first item's value
            array_path, field = path.split("[].", 1) if "[].]" in path else (path.rstrip("[]"), None)
            parts = array_path.split('.')
            current = data
            
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                    if current is None:
                        return None
                else:
                    return None
            
            # If we have an array, get first item's field
            if isinstance(current, list) and current and field:
                first_item = current[0]
                if isinstance(first_item, dict):
                    field_parts = field.split('.')
                    result = first_item
                    for fp in field_parts:
                        if isinstance(result, dict):
                            result = result.get(fp)
                            if result is None:
                                # No hardcoded field aliases - AI should map correctly
                                return None
                        else:
                            return None
                    return result
            
            return current
        
        # Regular path extraction
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            elif isinstance(current, list) and current:
                # If we hit a list, try to get from first item
                current = current[0] if isinstance(current[0], dict) else None
                if current:
                    current = current.get(part)
                if current is None:
                    return None
            else:
                return None
        
        return current
    
    def _apply_transform(self, value: Any, transform: str) -> str:
        """
        Apply transformation to value.
        
        Supported transforms:
        - date:FORMAT (e.g., "date:DD-MM-YYYY")
        - number:DECIMALS (e.g., "number:2")
        - currency:SYMBOL (e.g., "currency:₹")
        
        Args:
            value: Value to transform
            transform: Transform specification
            
        Returns:
            Transformed value as string
        """
        if value is None:
            return ""
        
        if transform.startswith("date:"):
            # Date formatting (simplified - can be enhanced)
            format_spec = transform.split(":", 1)[1]
            # For now, return as-is (can add proper date formatting)
            return str(value)
        
        elif transform.startswith("number:"):
            # Number formatting (remove commas, format as number)
            try:
                decimals = int(transform.split(":")[1])
                # Remove commas and convert to float
                if isinstance(value, str):
                    cleaned = value.replace(',', '').strip()
                else:
                    cleaned = str(value)
                num_value = float(cleaned) if cleaned else 0.0
                # Format without commas (Excel will handle formatting)
                return f"{num_value:.{decimals}f}"
            except (ValueError, TypeError):
                return str(value) if value else ""
        
        elif transform.startswith("currency:"):
            # Currency formatting
            symbol = transform.split(":")[1]
            try:
                num_value = float(value) if value else 0.0
                return f"{symbol}{num_value:.2f}"
            except (ValueError, TypeError):
                return str(value)
        
        # Default: return as string
        return str(value) if value is not None else ""
    
    def export_to_json(
        self,
        canonical: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Export canonical model to JSON (no template needed).
        
        Args:
            canonical: Canonical invoice model
            output_path: Output JSON file path
            
        Returns:
            Path to created JSON file
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(canonical, f, indent=2, default=str)
        
        return output_path
    
    def preview_export(
        self,
        canonical: Dict[str, Any],
        template: Dict[str, Any],
        max_rows: int = 10
    ) -> List[List[str]]:
        """
        Preview export without writing to file.
        
        Args:
            canonical: Canonical invoice model
            template: Template configuration
            max_rows: Maximum number of rows to preview
            
        Returns:
            List of rows (first row is headers)
        """
        columns = template.get("columns", [])
        headers = [col["header"] for col in columns]
        
        preview = [headers]
        
        if template.get("repeat") == "line_items":
            line_items = canonical.get("line_items", [])[:max_rows]
            for item in line_items:
                row = []
                for col in columns:
                    # Check for static value first
                    if "static_value" in col:
                        value = col["static_value"]
                    else:
                        path = col["path"]
                        if path.startswith("invoice.") or path.startswith("seller.") or \
                           path.startswith("buyer.") or path.startswith("totals."):
                            value = self._get_value_from_path(canonical, path)
                        else:
                            value = self._get_value_from_path(item, path)
                        
                        if col.get("transform"):
                            value = self._apply_transform(value, col["transform"])
                        elif value is None:
                            value = ""
                    
                    # Ensure value is properly formatted (avoid #### in Excel)
                    if value is None:
                        value = ""
                    elif isinstance(value, (int, float)):
                        # Format numbers as strings without commas
                        value = str(value)
                    else:
                        value = str(value)
                    
                    row.append(value)
                preview.append(row)
        else:
            row = []
            for col in columns:
                # Check for static value first
                if "static_value" in col:
                    value = col["static_value"]
                else:
                    value = self._get_value_from_path(canonical, col["path"])
                    if col.get("transform"):
                        value = self._apply_transform(value, col["transform"])
                row.append(str(value) if value is not None else "")
            preview.append(row)
        
        return preview
