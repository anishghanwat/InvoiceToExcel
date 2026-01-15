"""
Bulk invoice processing with parallel execution and progress tracking.
"""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import csv

from .pipeline import InvoiceProcessingPipeline
from .templates.template_parser import TemplateParser
from .templates.exporter import TemplateExporter
from src.utils.logger import get_logger
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import settings


class BulkInvoiceProcessor:
    """
    Process multiple invoices in parallel with progress tracking.
    
    Features:
    - Parallel processing with configurable workers
    - Progress tracking and reporting
    - Error handling per invoice
    - Consolidated output
    - Summary statistics
    """
    
    def __init__(
        self,
        max_workers: int = 3,
        use_ai: Optional[bool] = None,
        enable_logging: bool = True
    ):
        """
        Initialize bulk processor.
        
        Args:
            max_workers: Maximum number of parallel workers (default: 3)
            use_ai: Whether to use AI for canonical fixing
            enable_logging: Whether to enable structured logging
        """
        self.max_workers = max_workers
        self.pipeline = InvoiceProcessingPipeline(use_ai=use_ai, enable_logging=enable_logging)
        self.template_parser = TemplateParser()
        self.exporter = TemplateExporter()
        self.logger = get_logger() if enable_logging else None
    
    def process_directory(
        self,
        input_dir: str,
        template: Optional[Dict[str, Any]] = None,
        output_format: str = "csv",
        output_dir: str = "output",
        consolidated_output: bool = True,
        skip_existing: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process all invoices in a directory.
        
        Args:
            input_dir: Directory containing invoice files
            template: Template configuration (uses default if not provided)
            output_format: Output format ("csv", "json", "excel")
            output_dir: Directory for output files
            consolidated_output: Whether to create a single consolidated file
            skip_existing: Skip files that already have output
            progress_callback: Optional callback for progress updates (current, total, filename)
            
        Returns:
            Processing summary with statistics
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Find all invoice files
        invoice_files = self._find_invoice_files(input_path)
        
        if not invoice_files:
            return {
                "total": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
                "summary": "No invoice files found"
            }
        
        # Filter out already processed files if skip_existing
        skipped_count = 0
        if skip_existing:
            original_count = len(invoice_files)
            invoice_files = self._filter_existing_outputs(invoice_files, output_dir, output_format)
            skipped_count = original_count - len(invoice_files)
        
        total_files = len(invoice_files) + skipped_count
        
        if self.logger:
            self.logger.log_with_context('info', 'Bulk processing started', {
                "input_dir": input_dir,
                "total_files": total_files,
                "to_process": len(invoice_files),
                "skipped": skipped_count,
                "max_workers": self.max_workers
            })
        
        # Process invoices in parallel
        results = []
        start_time = time.time()
        
        if not invoice_files:
            return {
                "total": total_files,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": skipped_count,
                "results": [],
                "summary": "All files already processed"
            }
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    self._process_single_invoice,
                    str(file_path),
                    template,
                    output_format,
                    output_dir
                ): file_path
                for file_path in invoice_files
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(completed, len(invoice_files), Path(file_path).name)
                    
                    # Log progress
                    if result["success"]:
                        if self.logger:
                            self.logger.log_with_context('info', 'Invoice processed', {
                                "file": Path(file_path).name,
                                "status": "success",
                                "progress": f"{completed}/{len(invoice_files)}"
                            })
                    else:
                        if self.logger:
                            self.logger.log_error_with_context(
                                Exception(result.get("error", "Unknown error")),
                                f"Bulk processing: {Path(file_path).name}"
                            )
                    
                    status = "✅" if result["success"] else "❌"
                    print(f"{status} [{completed}/{len(invoice_files)}] {Path(file_path).name}")
                    
                except Exception as e:
                    results.append({
                        "file": str(file_path),
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    if self.logger:
                        self.logger.log_error_with_context(e, f"Bulk processing: {Path(file_path).name}")
        
        # Generate consolidated output if requested
        if consolidated_output and results:
            consolidated_path = self._create_consolidated_output(
                results,
                output_dir,
                output_format,
                template
            )
        else:
            consolidated_path = None
        
        # Calculate statistics
        successful = sum(1 for r in results if r.get("success"))
        failed = sum(1 for r in results if not r.get("success"))
        
        processing_time = time.time() - start_time
        
        summary = {
            "total": total_files,
            "processed": len(invoice_files),
            "successful": successful,
            "failed": failed,
            "skipped": skipped_count,
            "processing_time_seconds": processing_time,
            "average_time_per_invoice": processing_time / len(invoice_files) if invoice_files else 0,
            "results": results,
            "consolidated_output": consolidated_path
        }
        
        if self.logger:
            self.logger.log_with_context('info', 'Bulk processing completed', {
                "total": summary["total"],
                "successful": summary["successful"],
                "failed": summary["failed"],
                "skipped": summary["skipped"],
                "processing_time_seconds": processing_time
            })
        
        return summary
    
    def process_file_list(
        self,
        file_paths: List[str],
        template: Optional[Dict[str, Any]] = None,
        output_format: str = "csv",
        output_dir: str = "output",
        consolidated_output: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a list of invoice files.
        
        Args:
            file_paths: List of invoice file paths
            template: Template configuration
            output_format: Output format
            output_dir: Output directory
            consolidated_output: Whether to create consolidated output
            progress_callback: Optional progress callback
            
        Returns:
            Processing summary
        """
        # Validate files exist
        valid_files = []
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists():
                valid_files.append(path)
            else:
                print(f"⚠️  File not found: {file_path}")
        
        if not valid_files:
            return {
                "total": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "summary": "No valid files found"
            }
        
        # Process files
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(
                    self._process_single_invoice,
                    str(file_path),
                    template,
                    output_format,
                    output_dir
                ): file_path
                for file_path in valid_files
            }
            
            completed = 0
            total = len(valid_files)
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(completed, total, Path(file_path).name)
                    
                    status = "✅" if result["success"] else "❌"
                    print(f"{status} [{completed}/{total}] {Path(file_path).name}")
                    
                except Exception as e:
                    results.append({
                        "file": str(file_path),
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
        
        # Generate consolidated output
        if consolidated_output and results:
            consolidated_path = self._create_consolidated_output(
                results,
                output_dir,
                output_format,
                template
            )
        else:
            consolidated_path = None
        
        processing_time = time.time() - start_time
        successful = sum(1 for r in results if r.get("success"))
        failed = sum(1 for r in results if not r.get("success"))
        
        return {
            "total": len(file_paths),
            "processed": len(valid_files),
            "successful": successful,
            "failed": failed,
            "processing_time_seconds": processing_time,
            "average_time_per_invoice": processing_time / len(valid_files) if valid_files else 0,
            "results": results,
            "consolidated_output": consolidated_path
        }
    
    def _process_single_invoice(
        self,
        file_path: str,
        template: Optional[Dict[str, Any]],
        output_format: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Process a single invoice file."""
        try:
            result = self.pipeline.process_invoice(
                file_path=file_path,
                template=template,
                output_format=output_format,
                output_path=None  # Auto-generate
            )
            
            return {
                "file": file_path,
                "success": True,
                "canonical": result.get("canonical"),
                "validation": result.get("validation"),
                "output_file": result.get("output_file"),
                "processing_time_ms": result.get("processing_time_ms", 0)
            }
        except Exception as e:
            return {
                "file": file_path,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _find_invoice_files(self, directory: Path) -> List[Path]:
        """Find all invoice files in directory (deduplicated)."""
        supported_formats = {'.pdf', '.png', '.jpg', '.jpeg'}
        files = []
        seen_files = set()
        
        for ext in supported_formats:
            found_files = list(directory.glob(f"*{ext}")) + list(directory.glob(f"*{ext.upper()}"))
            for file_path in found_files:
                # Use absolute path to avoid duplicates
                abs_path = file_path.resolve()
                if abs_path not in seen_files:
                    seen_files.add(abs_path)
                    files.append(file_path)
        
        return sorted(files)
    
    def _filter_existing_outputs(
        self,
        invoice_files: List[Path],
        output_dir: str,
        output_format: str
    ) -> List[Path]:
        """Filter out files that already have output."""
        output_path = Path(output_dir)
        filtered = []
        
        for file_path in invoice_files:
            output_file = output_path / f"{file_path.stem}_export.{output_format}"
            if not output_file.exists():
                filtered.append(file_path)
        
        return filtered
    
    def _create_consolidated_output(
        self,
        results: List[Dict[str, Any]],
        output_dir: str,
        output_format: str,
        template: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Create a consolidated output file with all successful invoices."""
        successful_results = [r for r in results if r.get("success") and r.get("canonical")]
        
        if not successful_results:
            return None
        
        if output_format == "csv":
            return self._create_consolidated_csv(successful_results, output_dir, template)
        elif output_format == "json":
            return self._create_consolidated_json(successful_results, output_dir)
        else:
            return None
    
    def _create_consolidated_csv(
        self,
        results: List[Dict[str, Any]],
        output_dir: str,
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Create consolidated CSV with all invoices (deduplicated)."""
        if not template:
            template = self.template_parser.create_default_template()
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        consolidated_file = output_path / "consolidated_invoices.csv"
        
        # Check if template is for line items
        is_line_items_template = template.get("repeat") == "line_items"
        
        # Track processed files to avoid duplicates
        processed_files = set()
        
        if is_line_items_template:
            # Export all line items from all invoices
            all_rows = []
            
            for result in results:
                # Skip duplicates based on file path
                file_path = result.get("file", "")
                if file_path in processed_files:
                    continue
                processed_files.add(file_path)
                
                canonical = result.get("canonical")
                if not canonical:
                    continue
                    
                line_items = canonical.get("line_items", [])
                
                for item in line_items:
                    row = self._extract_row_from_item(item, template, canonical)
                    all_rows.append(row)
            
            # Write CSV
            try:
                with open(consolidated_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write headers
                    headers = [col.get("header", "") for col in template.get("columns", [])]
                    writer.writerow(headers)
                    # Write rows
                    writer.writerows(all_rows)
            except PermissionError:
                # File might be open, try with timestamp
                import time
                timestamp = int(time.time())
                consolidated_file = output_path / f"consolidated_invoices_{timestamp}.csv"
                with open(consolidated_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    headers = [col.get("header", "") for col in template.get("columns", [])]
                    writer.writerow(headers)
                    writer.writerows(all_rows)
                if self.logger:
                    self.logger.warning(f"Consolidated file was locked, created with timestamp: {consolidated_file.name}")
        else:
            # Export invoice-level data (deduplicated)
            all_rows = []
            
            for result in results:
                # Skip duplicates based on file path
                file_path = result.get("file", "")
                if file_path in processed_files:
                    continue
                processed_files.add(file_path)
                
                canonical = result.get("canonical")
                if not canonical:
                    continue
                    
                row = self._extract_row_from_canonical(canonical, template)
                all_rows.append(row)
            
            # Write CSV
            try:
                with open(consolidated_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write headers
                    headers = [col.get("header", "") for col in template.get("columns", [])]
                    writer.writerow(headers)
                    # Write rows
                    writer.writerows(all_rows)
            except PermissionError:
                # File might be open, try with timestamp
                import time
                timestamp = int(time.time())
                consolidated_file = output_path / f"consolidated_invoices_{timestamp}.csv"
                with open(consolidated_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    headers = [col.get("header", "") for col in template.get("columns", [])]
                    writer.writerow(headers)
                    writer.writerows(all_rows)
                if self.logger:
                    self.logger.warning(f"Consolidated file was locked, created with timestamp: {consolidated_file.name}")
        
        return str(consolidated_file)
    
    def _extract_row_from_canonical(
        self,
        canonical: Dict[str, Any],
        template: Dict[str, Any]
    ) -> List[str]:
        """Extract row values from canonical model based on template."""
        row = []
        for col in template.get("columns", []):
            path = col.get("path", "")
            value = self._get_value_by_path(canonical, path)
            # Apply transform if specified
            if value is not None and col.get("transform"):
                value = self._apply_transform(value, col["transform"])
            row.append(str(value) if value is not None else "")
        return row
    
    def _extract_row_from_item(
        self,
        item: Dict[str, Any],
        template: Dict[str, Any],
        canonical: Dict[str, Any]
    ) -> List[str]:
        """Extract row values from line item based on template."""
        row = []
        for col in template.get("columns", []):
            path = col.get("path", "")
            # Handle relative paths (e.g., "description" vs "line_items[].description")
            if path.startswith("line_items") or not "." in path:
                # Try item first
                clean_path = path.replace("line_items[].", "").replace("line_items.", "")
                value = self._get_value_by_path(item, clean_path)
                if value is None:
                    # Fallback to canonical
                    value = self._get_value_by_path(canonical, path)
            else:
                value = self._get_value_by_path(canonical, path)
            
            # Apply transform if specified
            if value is not None and col.get("transform"):
                value = self._apply_transform(value, col["transform"])
            
            row.append(str(value) if value is not None else "")
        return row
    
    def _get_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation path."""
        if not path:
            return None
        
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _apply_transform(self, value: Any, transform: str) -> str:
        """Apply transformation to value."""
        # Simple transform handling - can be extended
        if transform.startswith("date:"):
            # Date formatting would go here
            return str(value)
        elif transform.startswith("number:"):
            # Number formatting would go here
            return str(value)
        else:
            return str(value)
    
    def _create_consolidated_json(
        self,
        results: List[Dict[str, Any]],
        output_dir: str
    ) -> str:
        """Create consolidated JSON with all invoices."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        consolidated_file = output_path / "consolidated_invoices.json"
        
        consolidated_data = {
            "summary": {
                "total_invoices": len(results),
                "successful": sum(1 for r in results if r.get("success")),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "invoices": [r["canonical"] for r in results if r.get("success") and r.get("canonical")]
        }
        
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False, default=str)
        
        return str(consolidated_file)
