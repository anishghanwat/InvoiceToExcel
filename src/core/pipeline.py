"""
Main Processing Pipeline - Follows the new architecture.

Flow:
PDF / Image
   ↓
Textract
   ↓
Raw Signals (words, tables, kv)
   ↓
🧠 Canonical Invoice Model  ← accuracy happens here
   ↓
🧩 Template Engine          ← flexibility happens here
   ↓
CSV / Excel / JSON / API
"""
from typing import Dict, Any, Optional
import time
from .extraction.document_processor import DocumentProcessor
from .normalize.canonical_builder import CanonicalBuilder
from .ai.canonical_fixer import CanonicalFixer
from .validators.validator import ValidationEngine
from .templates.template_parser import TemplateParser
from .templates.exporter import TemplateExporter


class InvoiceProcessingPipeline:
    """
    Main pipeline that processes invoices following the new architecture.
    
    Key principles:
    - Extraction ≠ Output format
    - Canonical model is stable, templates are unlimited
    - AI works only with canonical JSON
    - Validation before export
    """
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize pipeline.
        
        Args:
            use_ai: Whether to use AI for canonical fixing
        """
        self.document_processor = DocumentProcessor()
        self.canonical_builder = CanonicalBuilder()
        self.ai_fixer = CanonicalFixer() if use_ai else None
        self.validator = ValidationEngine()
        self.template_parser = TemplateParser()
        self.exporter = TemplateExporter()
    
    def process_invoice(
        self,
        file_path: str,
        template: Optional[Dict[str, Any]] = None,
        output_format: str = "csv",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process invoice from file to output format.
        
        Args:
            file_path: Path to invoice file (PDF, image)
            template: Optional template configuration (uses default if not provided)
            output_format: Output format ("csv", "json", "excel")
            output_path: Optional output file path
            
        Returns:
            Processing result with canonical model, validation, and output path
        """
        start_time = time.time()
        
        # Step 1: Extract with Textract
        print("📄 Step 1: Extracting with Textract...")
        textract_results = self.document_processor.process_document(file_path, output_dir="output")
        
        # Extract document text for context
        document_text = self._extract_document_text(textract_results)
        
        # Step 2: Build canonical model
        print("🧠 Step 2: Building canonical invoice model...")
        canonical = self.canonical_builder.build(textract_results, document_text)
        
        # Step 3: AI fixing (if enabled and needed)
        # Only use AI if there are validation errors or missing critical fields
        use_ai_fix = False
        if self.ai_fixer:
            # Check if we need AI fixing
            missing_critical = (
                not canonical.get("invoice", {}).get("invoice_number") or
                not canonical.get("invoice", {}).get("invoice_date") or
                not canonical.get("seller", {}).get("name") or
                not canonical.get("buyer", {}).get("name")
            )
            use_ai_fix = missing_critical
        
        if use_ai_fix and self.ai_fixer:
            print("🤖 Step 3: AI fixing canonical model (filling missing critical fields)...")
            canonical, ai_confidences = self.ai_fixer.fix_canonical(
                canonical,
                textract_results,
                document_text
            )
            # Update confidence scores
            if ai_confidences:
                canonical["metadata"]["confidence"]["fields"].update(ai_confidences)
        elif self.ai_fixer:
            print("🤖 Step 3: AI fixing (skipped - all critical fields present)")
        
        # Step 4: Validation
        print("✅ Step 4: Validating canonical model...")
        validation_result = self.validator.validate(canonical)
        
        if not validation_result["valid"]:
            print(f"⚠️  Validation found {len(validation_result['errors'])} errors:")
            for error in validation_result["errors"]:
                print(f"   - {error}")
        
        # Step 5: Export using template
        output_file = None
        if output_format in ["csv", "excel"]:
            if template is None:
                # Use default template
                template = self.template_parser.create_default_template()
            
            print(f"📊 Step 5: Exporting to {output_format.upper()}...")
            if output_path is None:
                from pathlib import Path
                input_path = Path(file_path)
                output_path = f"output/{input_path.stem}_export.{output_format}"
            
            output_file = self.exporter.export_to_csv(canonical, template, output_path)
            print(f"✅ Exported to: {output_file}")
        
        elif output_format == "json":
            if output_path is None:
                from pathlib import Path
                input_path = Path(file_path)
                output_path = f"output/{input_path.stem}_canonical.json"
            
            output_file = self.exporter.export_to_json(canonical, output_path)
            print(f"✅ Exported to: {output_file}")
        
        # Update metadata
        processing_time = int((time.time() - start_time) * 1000)
        canonical["metadata"]["processing_time_ms"] = processing_time
        
        # Calculate overall confidence
        field_confidences = canonical["metadata"]["confidence"]["fields"]
        if field_confidences:
            overall = sum(field_confidences.values()) / len(field_confidences)
        else:
            overall = 0.5  # Default if no confidence scores
        canonical["metadata"]["confidence"]["overall"] = overall
        
        return {
            "canonical": canonical,
            "validation": validation_result,
            "output_file": output_file,
            "processing_time_ms": processing_time
        }
    
    def _extract_document_text(self, textract_results: Dict[str, Any]) -> str:
        """Extract full document text from Textract results."""
        text_blocks = textract_results.get('text_blocks', [])
        return ' '.join(block.get('text', '') for block in text_blocks)
