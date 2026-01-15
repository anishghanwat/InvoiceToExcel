"""
AWS Textract client for document analysis with production-grade error handling.
"""
import boto3
import json
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.utils.retry import retry_aws_operation, is_retryable_aws_error, NonRetryableError


class TextractClient:
    """Client for AWS Textract document analysis with retry logic."""
    
    def __init__(self, region_name: str = 'us-east-1', max_retries: int = 3):
        """
        Initialize Textract client.
        
        Args:
            region_name: AWS region for Textract
            max_retries: Maximum number of retry attempts for API calls
        """
        try:
            self.textract = boto3.client('textract', region_name=region_name)
            self.region = region_name
            self.max_retries = max_retries
        except NoCredentialsError:
            raise NonRetryableError("AWS credentials not found. Please configure your credentials.")
        except Exception as e:
            raise NonRetryableError(f"Failed to initialize Textract client: {str(e)}")
    
    def analyze_document(self, document_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze document using AWS Textract AnalyzeDocument API with retry logic.
        
        Args:
            document_bytes: Document content as bytes
            
        Returns:
            Dict containing Textract analysis results
            
        Raises:
            NonRetryableError: For non-retryable errors (invalid input, auth, etc.)
            Exception: For retryable errors that exhausted all retries
        """
        def _analyze():
            """Inner function for retry logic."""
            try:
                response = self.textract.analyze_document(
                    Document={'Bytes': document_bytes},
                    FeatureTypes=['TABLES', 'FORMS']
                )
                return response
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                # Check if retryable
                if not is_retryable_aws_error(e):
                    raise NonRetryableError(
                        f"Textract API error ({error_code}): {error_message}"
                    ) from e
                
                # Re-raise for retry logic
                raise
        
        # Retry with exponential backoff
        def on_retry(attempt: int, error: Exception):
            """Callback for retry events."""
            error_code = error.response.get('Error', {}).get('Code', 'Unknown') if hasattr(error, 'response') else 'Unknown'
            print(f"⚠️  Textract API retry {attempt}/{self.max_retries} (Error: {error_code})...")
        
        try:
            return retry_aws_operation(
                _analyze,
                max_retries=self.max_retries,
                initial_delay=1.0,
                max_delay=60.0,
                on_retry=on_retry
            )
        except NonRetryableError:
            raise
        except Exception as e:
            raise Exception(f"Textract analysis failed after retries: {str(e)}") from e
    
    def format_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Textract response for better readability.
        
        Args:
            response: Raw Textract response
            
        Returns:
            Formatted response with organized data
        """
        formatted = {
            'document_metadata': response.get('DocumentMetadata', {}),
            'blocks': response.get('Blocks', []),
            'analyze_document_model_version': response.get('AnalyzeDocumentModelVersion', ''),
            'summary': {
                'total_blocks': len(response.get('Blocks', [])),
                'pages': 0,
                'lines': 0,
                'words': 0,
                'key_value_pairs': 0,
                'tables': 0,
                'cells': 0
            }
        }
        
        # Count different block types
        for block in response.get('Blocks', []):
            block_type = block.get('BlockType', '')
            if block_type == 'PAGE':
                formatted['summary']['pages'] += 1
            elif block_type == 'LINE':
                formatted['summary']['lines'] += 1
            elif block_type == 'WORD':
                formatted['summary']['words'] += 1
            elif block_type == 'KEY_VALUE_SET':
                formatted['summary']['key_value_pairs'] += 1
            elif block_type == 'TABLE':
                formatted['summary']['tables'] += 1
            elif block_type == 'CELL':
                formatted['summary']['cells'] += 1
        
        return formatted
    
    def extract_text_blocks(self, response: Dict[str, Any]) -> list:
        """
        Extract all text blocks from Textract response.
        
        Args:
            response: Textract response
            
        Returns:
            List of text blocks with their properties
        """
        text_blocks = []
        
        for block in response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text_blocks.append({
                    'id': block.get('Id'),
                    'text': block.get('Text', ''),
                    'confidence': block.get('Confidence', 0),
                    'geometry': block.get('Geometry', {}),
                    'block_type': 'LINE'
                })
        
        return text_blocks
    
    def extract_key_value_pairs(self, response: Dict[str, Any]) -> list:
        """
        Extract key-value pairs from Textract response.
        
        Args:
            response: Textract response
            
        Returns:
            List of key-value pairs
        """
        key_value_pairs = []
        blocks = response.get('Blocks', [])
        
        # Create a map of block IDs to blocks for easy lookup
        block_map = {block['Id']: block for block in blocks}
        
        for block in blocks:
            if block.get('BlockType') == 'KEY_VALUE_SET':
                if block.get('EntityTypes') and 'KEY' in block['EntityTypes']:
                    # This is a key block
                    key_text = self._get_text_from_relationships(block, block_map)
                    
                    # Find the corresponding value
                    value_text = ''
                    if 'Relationships' in block:
                        for relationship in block['Relationships']:
                            if relationship['Type'] == 'VALUE':
                                for value_id in relationship['Ids']:
                                    value_block = block_map.get(value_id)
                                    if value_block:
                                        value_text = self._get_text_from_relationships(value_block, block_map)
                    
                    key_value_pairs.append({
                        'key': key_text,
                        'value': value_text,
                        'key_confidence': block.get('Confidence', 0),
                        'key_id': block.get('Id')
                    })
        
        return key_value_pairs
    
    def extract_tables(self, response: Dict[str, Any]) -> list:
        """
        Extract tables from Textract response.
        
        Args:
            response: Textract response
            
        Returns:
            List of tables, each as a list of rows (each row is a list of cells)
        """
        tables = []
        blocks = response.get('Blocks', [])
        block_map = {block['Id']: block for block in blocks}
        
        for block in blocks:
            if block.get('BlockType') == 'TABLE':
                table = self._extract_table_structure(block, block_map)
                if table:
                    tables.append(table)
        
        return tables
    
    def _extract_table_structure(self, table_block: Dict[str, Any], block_map: Dict[str, Any]) -> list:
        """
        Extract structured table data from a TABLE block.
        
        Args:
            table_block: The TABLE block
            block_map: Map of block IDs to blocks
            
        Returns:
            List of rows, each row is a list of cell values
        """
        rows = []
        cells = {}
        
        # First, collect all cells
        if 'Relationships' in table_block:
            for relationship in table_block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for cell_id in relationship['Ids']:
                        cell_block = block_map.get(cell_id)
                        if cell_block and cell_block.get('BlockType') == 'CELL':
                            row_index = cell_block.get('RowIndex', 0)
                            col_index = cell_block.get('ColumnIndex', 0)
                            cell_text = self._get_text_from_relationships(cell_block, block_map)
                            
                            if row_index not in cells:
                                cells[row_index] = {}
                            cells[row_index][col_index] = cell_text
        
        # Convert to list of rows
        if cells:
            max_row = max(cells.keys())
            max_col = max(max(row.keys()) for row in cells.values() if row)
            
            for row_idx in range(1, max_row + 1):  # Start from 1 (0 is usually header)
                row = []
                for col_idx in range(1, max_col + 1):
                    cell_value = cells.get(row_idx, {}).get(col_idx, '')
                    row.append(cell_value)
                if any(cell.strip() for cell in row):  # Only add non-empty rows
                    rows.append(row)
        
        return rows
    
    def _get_text_from_relationships(self, block: Dict[str, Any], block_map: Dict[str, Any]) -> str:
        """
        Extract text from a block's child relationships.
        
        Args:
            block: The block to extract text from
            block_map: Map of block IDs to blocks
            
        Returns:
            Concatenated text from child blocks
        """
        text = ''
        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        child_block = block_map.get(child_id)
                        if child_block:
                            if child_block.get('BlockType') == 'WORD':
                                text += child_block.get('Text', '') + ' '
                            elif child_block.get('BlockType') == 'LINE':
                                text += child_block.get('Text', '') + ' '
        return text.strip()