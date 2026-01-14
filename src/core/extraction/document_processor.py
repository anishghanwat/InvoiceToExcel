"""
Document processor for handling file uploads and Textract analysis.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from .textract_client import TextractClient


class DocumentProcessor:
    """Handles document processing workflow."""
    
    SUPPORTED_FORMATS = {'.pdf', '.png', '.jpg', '.jpeg'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, aws_region: str = 'us-east-1'):
        """Initialize document processor."""
        self.textract_client = TextractClient(region_name=aws_region)
    
    def validate_file(self, file_path: str) -> bool:
        """
        Validate if file is supported and within size limits.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is valid
            
        Raises:
            Exception: If file is invalid
        """
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            raise Exception(f"Unsupported file format: {file_ext}. Supported: {', '.join(self.SUPPORTED_FORMATS)}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise Exception(f"File too large: {file_size / (1024*1024):.1f}MB. Max size: {self.MAX_FILE_SIZE / (1024*1024)}MB")
        
        return True
    
    def process_document(self, file_path: str, output_dir: str = "output") -> Dict[str, Any]:
        """
        Process document through complete workflow.
        
        Args:
            file_path: Path to input document
            output_dir: Directory to save output files
            
        Returns:
            Dict containing processing results
        """
        print(f"Processing document: {file_path}")
        
        # Validate file
        self.validate_file(file_path)
        print("✓ File validation passed")
        
        # Read file
        with open(file_path, 'rb') as file:
            document_bytes = file.read()
        
        print("✓ File loaded")
        
        # Analyze with Textract
        print("Analyzing document with AWS Textract...")
        raw_response = self.textract_client.analyze_document(document_bytes)
        print("✓ Textract analysis complete")
        
        # Format response
        formatted_response = self.textract_client.format_response(raw_response)
        
        # Extract structured data
        text_blocks = self.textract_client.extract_text_blocks(raw_response)
        key_value_pairs = self.textract_client.extract_key_value_pairs(raw_response)
        tables = self.textract_client.extract_tables(raw_response)
        
        # Prepare results
        results = {
            'input_file': file_path,
            'summary': formatted_response['summary'],
            'text_blocks': text_blocks,
            'key_value_pairs': key_value_pairs,
            'tables': tables,
            'raw_textract_response': raw_response,
            'formatted_response': formatted_response
        }
        
        # Save results
        os.makedirs(output_dir, exist_ok=True)
        self._save_results(results, output_dir, Path(file_path).stem)
        
        return results
    
    def _save_results(self, results: Dict[str, Any], output_dir: str, filename_base: str):
        """
        Save processing results to files.
        
        Args:
            results: Processing results
            output_dir: Output directory
            filename_base: Base filename for output files
        """
        # Save complete results as JSON
        results_file = os.path.join(output_dir, f"{filename_base}_results.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            # Create a copy without the raw response for cleaner JSON
            clean_results = results.copy()
            clean_results.pop('raw_textract_response', None)
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        print(f"✓ Results saved to: {results_file}")
        
        # Save raw Textract response separately
        raw_file = os.path.join(output_dir, f"{filename_base}_raw_textract.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(results['raw_textract_response'], f, indent=2, ensure_ascii=False)
        print(f"✓ Raw Textract response saved to: {raw_file}")
        
        # Save extracted text as plain text
        text_file = os.path.join(output_dir, f"{filename_base}_extracted_text.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("EXTRACTED TEXT BLOCKS:\n")
            f.write("=" * 50 + "\n\n")
            for i, block in enumerate(results['text_blocks'], 1):
                f.write(f"Block {i} (Confidence: {block['confidence']:.1f}%):\n")
                f.write(f"{block['text']}\n\n")
            
            f.write("\nKEY-VALUE PAIRS:\n")
            f.write("=" * 50 + "\n\n")
            for i, kv in enumerate(results['key_value_pairs'], 1):
                f.write(f"Pair {i}:\n")
                f.write(f"  Key: {kv['key']}\n")
                f.write(f"  Value: {kv['value']}\n")
                f.write(f"  Confidence: {kv['key_confidence']:.1f}%\n\n")
        
        print(f"✓ Extracted text saved to: {text_file}")
    
    def print_summary(self, results: Dict[str, Any]):
        """
        Print a summary of processing results.
        
        Args:
            results: Processing results
        """
        summary = results['summary']
        
        print("\n" + "=" * 60)
        print("DOCUMENT ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Input File: {results['input_file']}")
        print(f"Pages: {summary['pages']}")
        print(f"Text Lines: {summary['lines']}")
        print(f"Words: {summary['words']}")
        print(f"Key-Value Pairs: {summary['key_value_pairs']}")
        print(f"Tables: {summary['tables']}")
        print(f"Table Cells: {summary['cells']}")
        
        print(f"\nExtracted {len(results['text_blocks'])} text blocks")
        print(f"Found {len(results['key_value_pairs'])} key-value pairs")
        
        if results['key_value_pairs']:
            print("\nSample Key-Value Pairs:")
            for i, kv in enumerate(results['key_value_pairs'][:5], 1):
                print(f"  {i}. {kv['key']} → {kv['value']}")
            if len(results['key_value_pairs']) > 5:
                print(f"  ... and {len(results['key_value_pairs']) - 5} more")
        
        print("=" * 60)