"""
CSV configuration models.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ColumnMapping:
    """Represents mapping of a column to extracted data."""
    column_name: str
    matched_values: List[str] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    mapping_strategy: str = ""  # keyword, pattern, fuzzy, etc.


@dataclass
class CSVConfig:
    """Configuration for CSV generation."""
    
    columns: List[str] = field(default_factory=list)
    column_mappings: Dict[str, ColumnMapping] = field(default_factory=dict)
    output_file: str = ""
    include_confidence: bool = False
    max_rows: Optional[int] = None
    
    def add_column(self, column_name: str) -> None:
        """Add a new column to the configuration."""
        if column_name not in self.columns:
            self.columns.append(column_name)
            self.column_mappings[column_name] = ColumnMapping(column_name=column_name)
    
    def set_column_mapping(self, column_name: str, values: List[str], strategy: str = "") -> None:
        """Set mapping for a specific column."""
        if column_name not in self.column_mappings:
            self.add_column(column_name)
        
        self.column_mappings[column_name].matched_values = values
        self.column_mappings[column_name].mapping_strategy = strategy
    
    def get_total_data_points(self) -> int:
        """Get total number of data points across all columns."""
        return sum(len(mapping.matched_values) for mapping in self.column_mappings.values())
    
    def get_filled_columns_count(self) -> int:
        """Get number of columns that have data."""
        return sum(1 for mapping in self.column_mappings.values() if mapping.matched_values)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'columns': self.columns,
            'column_mappings': {
                name: {
                    'column_name': mapping.column_name,
                    'matched_values': mapping.matched_values,
                    'confidence_scores': mapping.confidence_scores,
                    'mapping_strategy': mapping.mapping_strategy
                }
                for name, mapping in self.column_mappings.items()
            },
            'output_file': self.output_file,
            'include_confidence': self.include_confidence,
            'max_rows': self.max_rows
        }