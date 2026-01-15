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
import traceback
from pathlib import Path
from .extraction.document_processor import DocumentProcessor
from .normalize.canonical_builder import CanonicalBuilder
from .ai.canonical_fixer import CanonicalFixer
from .validators.validator import ValidationEngine
from .templates.template_parser import TemplateParser
from .templates.exporter import TemplateExporter
from src.utils.logger import get_logger
from src.utils.timeout import TimeoutGuard, TimeoutError
import sys
from pathlib import Path

# Add project root to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import settings


class InvoiceProcessingPipeline:
    """
    Main pipeline that processes invoices following the new architecture.
    
    Key principles:
    - Extraction ≠ Output format
    - Canonical model is stable, templates are unlimited
    - AI works only with canonical JSON
    - Validation before export
    """
    
    def __init__(self, use_ai: Optional[bool] = None, enable_logging: Optional[bool] = None, timeout_seconds: Optional[float] = None):
        """
        Initialize pipeline with production-ready defaults.
        
        Args:
            use_ai: Whether to use AI for canonical fixing (defaults to settings.ENABLE_AI_FIXING)
            enable_logging: Whether to enable structured logging (defaults to settings.ENABLE_STRUCTURED_LOGGING)
            timeout_seconds: Maximum processing time in seconds (defaults to settings.PIPELINE_TIMEOUT_SECONDS)
        """
        self.document_processor = DocumentProcessor()
        self.canonical_builder = CanonicalBuilder()
        use_ai = use_ai if use_ai is not None else settings.ENABLE_AI_FIXING
        self.ai_fixer = CanonicalFixer(max_retries=settings.AI_MAX_RETRIES) if use_ai else None
        self.validator = ValidationEngine()
        self.template_parser = TemplateParser()
        self.exporter = TemplateExporter()
        enable_logging = enable_logging if enable_logging is not None else settings.ENABLE_STRUCTURED_LOGGING
        self.logger = get_logger() if enable_logging else None
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.PIPELINE_TIMEOUT_SECONDS
        self.graceful_degradation = settings.ENABLE_GRACEFUL_DEGRADATION
    
    def process_invoice(
        self,
        file_path: str,
        template: Optional[Dict[str, Any]] = None,
        output_format: str = "csv",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process invoice from file to output format with comprehensive error handling.
        
        Args:
            file_path: Path to invoice file (PDF, image)
            template: Optional template configuration (uses default if not provided)
            output_format: Output format ("csv", "json", "excel")
            output_path: Optional output file path
            
        Returns:
            Processing result with canonical model, validation, and output path
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is invalid
            Exception: For processing errors with detailed context
        """
        start_time = time.time()
        error_context = {"step": None, "file": file_path}
        timeout_guard = TimeoutGuard(self.timeout_seconds)
        
        if self.logger:
            self.logger.log_with_context('info', 'Pipeline started', {"file": file_path, "timeout_seconds": self.timeout_seconds})
        
        try:
            # Validate input file
            timeout_guard.check()
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Invoice file not found: {file_path}")
            
            # Step 1: Extract with Textract
            error_context["step"] = "Textract Extraction"
            step_start = time.time()
            print("📄 Step 1: Extracting with Textract...")
            try:
                timeout_guard.check()
                textract_results = self.document_processor.process_document(file_path, output_dir="output")
                step_duration = (time.time() - step_start) * 1000
                if self.logger:
                    self.logger.log_performance("Textract Extraction", step_duration, {"file": file_path})
            except TimeoutError:
                raise
            except Exception as e:
                if self.logger:
                    self.logger.log_error_with_context(e, "Textract Extraction")
                raise Exception(f"Textract extraction failed: {str(e)}") from e
            
            # Extract document text for context
            document_text = self._extract_document_text(textract_results)
            
            # Step 2: Build canonical model
            error_context["step"] = "Canonical Model Building"
            step_start = time.time()
            print("🧠 Step 2: Building canonical invoice model...")
            try:
                timeout_guard.check()
                canonical = self.canonical_builder.build(textract_results, document_text)
                step_duration = (time.time() - step_start) * 1000
                if self.logger:
                    self.logger.log_performance("Canonical Building", step_duration, {"file": file_path})
            except TimeoutError:
                raise
            except Exception as e:
                if self.logger:
                    self.logger.log_error_with_context(e, "Canonical Model Building")
                raise Exception(f"Canonical model building failed: {str(e)}") from e
            
            # Step 3: AI fixing (if enabled and needed)
            error_context["step"] = "AI Fixing"
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
                try:
                    canonical, ai_confidences = self.ai_fixer.fix_canonical(
                        canonical,
                        textract_results,
                        document_text
                    )
                    # Update confidence scores
                    if ai_confidences:
                        canonical["metadata"]["confidence"]["fields"].update(ai_confidences)
                except Exception as e:
                    error_msg = f"AI fixing failed: {str(e)}"
                    if self.logger:
                        self.logger.log_error_with_context(e, "AI Fixing")
                    if self.graceful_degradation:
                        print(f"⚠️  {error_msg}. Continuing with original canonical.")
                        # Continue with original canonical if AI fails
                    else:
                        raise Exception(error_msg) from e
            elif self.ai_fixer:
                print("🤖 Step 3: AI fixing (skipped - all critical fields present)")
            
            # Step 4: Validation
            error_context["step"] = "Validation"
            print("✅ Step 4: Validating canonical model...")
            try:
                validation_result = self.validator.validate(canonical)
            except Exception as e:
                print(f"⚠️  Validation error: {str(e)}. Continuing without validation.")
                validation_result = {"valid": False, "errors": [f"Validation failed: {str(e)}"]}
            
            if not validation_result["valid"]:
                print(f"⚠️  Validation found {len(validation_result['errors'])} errors:")
                for error in validation_result["errors"]:
                    print(f"   - {error}")
            
            # Step 5: Export using template
            error_context["step"] = "Export"
            output_file = None
            if output_format in ["csv", "excel"]:
                if template is None:
                    # Use default template
                    template = self.template_parser.create_default_template()
                
                print(f"📊 Step 5: Exporting to {output_format.upper()}...")
                if output_path is None:
                    input_path = Path(file_path)
                    output_path = f"output/{input_path.stem}_export.{output_format}"
                
                try:
                    output_file = self.exporter.export_to_csv(canonical, template, output_path)
                    print(f"✅ Exported to: {output_file}")
                except Exception as e:
                    raise Exception(f"Export to {output_format} failed: {str(e)}") from e
            
            elif output_format == "json":
                if output_path is None:
                    input_path = Path(file_path)
                    output_path = f"output/{input_path.stem}_canonical.json"
                
                try:
                    output_file = self.exporter.export_to_json(canonical, output_path)
                    print(f"✅ Exported to: {output_file}")
                except Exception as e:
                    raise Exception(f"Export to JSON failed: {str(e)}") from e
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
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
                "processing_time_ms": processing_time,
                "success": True
            }
            
        except (FileNotFoundError, ValueError, TimeoutError):
            raise
        except Exception as e:
            # Add context to error message
            error_msg = f"Pipeline error at {error_context['step']} for {error_context['file']}: {str(e)}"
            if self.logger:
                self.logger.log_error_with_context(e, error_context['step'] or "Unknown")
            print(f"❌ {error_msg}")
            if self.logger:
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            raise Exception(error_msg) from e
    
    def _extract_document_text(self, textract_results: Dict[str, Any]) -> str:
        """Extract full document text from Textract results."""
        text_blocks = textract_results.get('text_blocks', [])
        return ' '.join(block.get('text', '') for block in text_blocks)
