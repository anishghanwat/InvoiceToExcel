"""
CSV export functionality.
"""
import csv
import os
from typing import List, Dict, Any, Optional
from ..mapping.csv_mapper import CSVMapper
from ...models.csv_config import CSVConfig
from ...utils.file_utils import FileUtils


class CSVExporter:
    """Handles CSV file export functionality."""
    
    def __init__(self):
        """Initialize CSV exporter."""
        pass
    
    def export_to_csv(self, csv_config: CSVConfig, output_path: str) -> str:
        """
        Export data to CSV file based on configuration.
        
        Args:
            csv_config: CSV configuration with columns and mappings
            output_path: Output file path
            
        Returns:
            Path to created CSV file
        """
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            FileUtils.ensure_directory(output_dir)
        
        # Determine number of rows needed
        max_rows = max(
            len(mapping.matched_values) 
            for mapping in csv_config.column_mappings.values()
        ) if csv_config.column_mappings else 1
        
        # Apply max_rows limit if specified
        if csv_config.max_rows and max_rows > csv_config.max_rows:
            max_rows = csv_config.max_rows
        
        # Create CSV data
        csv_data = []
        
        # Add header row
        headers = csv_config.columns.copy()
        if csv_config.include_confidence:
            # Add confidence columns
            confidence_headers = [f"{col}_confidence" for col in csv_config.columns]
            headers.extend(confidence_headers)
        
        csv_data.append(headers)
        
        # Add data rows
        for row_idx in range(max_rows):
            row = []
            
            # Add data columns
            for column in csv_config.columns:
                mapping = csv_config.column_mappings.get(column)
                if mapping and row_idx < len(mapping.matched_values):
                    row.append(mapping.matched_values[row_idx])
                else:
                    row.append('')  # Empty cell if no data
            
            # Add confidence columns if requested
            if csv_config.include_confidence:
                for column in csv_config.columns:
                    mapping = csv_config.column_mappings.get(column)
                    if mapping and row_idx < len(mapping.confidence_scores):
                        row.append(f"{mapping.confidence_scores[row_idx]:.1f}%")
                    else:
                        row.append('')
            
            csv_data.append(row)
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(csv_data)
        
        return output_path
    
    def export_simple_csv(self, columns: List[str], mappings: Dict[str, List[str]], output_path: str) -> str:
        """
        Export simple CSV without configuration object.
        
        Args:
            columns: Column names
            mappings: Column to data mappings
            output_path: Output file path
            
        Returns:
            Path to created CSV file
        """
        # Create CSV config from simple parameters
        csv_config = CSVConfig(columns=columns)
        
        for column, values in mappings.items():
            csv_config.set_column_mapping(column, values)
        
        return self.export_to_csv(csv_config, output_path)
    
    def preview_csv(self, csv_config: CSVConfig, max_preview_rows: int = 10) -> List[List[str]]:
        """
        Generate preview of CSV data without writing to file.
        
        Args:
            csv_config: CSV configuration
            max_preview_rows: Maximum rows to include in preview
            
        Returns:
            List of CSV rows (including header)
        """
        # Determine number of rows for preview
        max_rows = max(
            len(mapping.matched_values) 
            for mapping in csv_config.column_mappings.values()
        ) if csv_config.column_mappings else 1
        
        preview_rows = min(max_rows, max_preview_rows)
        
        # Create preview data
        preview_data = []
        
        # Add header
        preview_data.append(csv_config.columns.copy())
        
        # Add data rows
        for row_idx in range(preview_rows):
            row = []
            for column in csv_config.columns:
                mapping = csv_config.column_mappings.get(column)
                if mapping and row_idx < len(mapping.matched_values):
                    row.append(mapping.matched_values[row_idx])
                else:
                    row.append('')
            preview_data.append(row)
        
        return preview_data