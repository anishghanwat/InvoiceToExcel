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
from .ai.semantic_extractor import SemanticExtractor
from .ai.schema_inferencer import SchemaInferencer
from .ai.dynamic_mapper import DynamicMapper
from .ai.semantic_validator import SemanticValidator
from .ai.learning_engine import LearningEngine
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
        
        # New AI-driven components
        if use_ai:
            self.semantic_extractor = SemanticExtractor()
            self.schema_inferencer = SchemaInferencer()
            self.dynamic_mapper = DynamicMapper()
            self.semantic_validator = SemanticValidator()
            self.learning_engine = LearningEngine()
        else:
            self.semantic_extractor = None
            self.schema_inferencer = None
            self.dynamic_mapper = None
            self.semantic_validator = None
            self.learning_engine = None
        
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
            
            # Step 2: Create empty canonical structure
            error_context["step"] = "Canonical Structure Creation"
            step_start = time.time()
            print("🧠 Step 2: Creating canonical invoice structure...")
            try:
                timeout_guard.check()
                canonical = self.canonical_builder.create_empty()
                step_duration = (time.time() - step_start) * 1000
                if self.logger:
                    self.logger.log_performance("Canonical Structure", step_duration, {"file": file_path})
            except TimeoutError:
                raise
            except Exception as e:
                if self.logger:
                    self.logger.log_error_with_context(e, "Canonical Structure Creation")
                raise Exception(f"Canonical structure creation failed: {str(e)}") from e
            
            # Step 3: Semantic Extraction (AI-driven - replaces keyword matching)
            error_context["step"] = "Semantic Extraction"
            if self.semantic_extractor:
                print("🤖 Step 3: Extracting invoice data using AI (semantic understanding)...")
                try:
                    timeout_guard.check()
                    # Pass base canonical structure to extractor - it will merge AI response into it
                    canonical = self.semantic_extractor.extract_all_fields(
                        textract_results,
                        document_text,
                        base_canonical=canonical  # Pass base structure for merging
                    )
                    print("✅ AI extraction complete - all fields extracted semantically")
                except Exception as e:
                    error_msg = f"Semantic extraction failed: {str(e)}"
                    if self.logger:
                        self.logger.log_error_with_context(e, "Semantic Extraction")
                    if self.graceful_degradation:
                        print(f"⚠️  {error_msg}. Continuing with empty canonical.")
                        # Keep empty canonical - at least structure is valid
                    else:
                        raise Exception(error_msg) from e
            else:
                print("🤖 Step 3: Semantic extraction (skipped - AI not available)")
            
            # Step 4: Schema Inference (if template is CSV)
            error_context["step"] = "Schema Inference"
            if template and self.schema_inferencer:
                # Check if template needs inference (CSV headers)
                if isinstance(template, dict) and 'columns' in template:
                    columns = template.get('columns', [])
                    # If columns don't have canonical_path, infer schema
                    needs_inference = any(
                        not col.get('canonical_path') or col.get('canonical_path', '').startswith('unknown.')
                        for col in columns
                    )
                    if needs_inference:
                        print("🔍 Step 4: Inferring template schema using AI...")
                        try:
                            csv_headers = [col.get('header', '') for col in columns]
                            inferred_schema = self.schema_inferencer.infer_schema(
                                csv_headers,
                                canonical_sample=canonical
                            )
                            # Update template with inferred schema
                            template = inferred_schema
                            print("✅ Schema inference complete")
                        except Exception as e:
                            print(f"⚠️  Schema inference failed: {e}. Using existing template.")
            
            # Step 5: Dynamic Mapping (AI-driven - maps canonical to template)
            error_context["step"] = "Dynamic Mapping"
            mapped_data = None
            if template and self.dynamic_mapper:
                print("🗺️  Step 5: Mapping invoice data to template using AI...")
                print(f"🔍 [PIPELINE] Canonical before mapping - keys: {list(canonical.keys())}")
                print(f"🔍 [PIPELINE] Canonical invoice_number: {canonical.get('invoice', {}).get('invoice_number')}")
                print(f"🔍 [PIPELINE] Canonical buyer name: {canonical.get('buyer', {}).get('name')}")
                print(f"🔍 [PIPELINE] Canonical total: {canonical.get('totals', {}).get('total')}")
                
                try:
                    timeout_guard.check()
                    # Get mapping history from learning engine
                    mapping_history = None
                    if self.learning_engine:
                        template_profile = self.learning_engine.get_template_profile(template)
                        if template_profile:
                            mapping_history = template_profile.get('mappings', [])
                    
                    mapped_data = self.dynamic_mapper.map_to_template(
                        canonical,
                        template,
                        mapping_history,
                        document_text=document_text
                    )
                    print(f"🔍 [PIPELINE] Mapped data received: {mapped_data}")
                    print("✅ Dynamic mapping complete")
                except Exception as e:
                    error_msg = f"Dynamic mapping failed: {str(e)}"
                    if self.logger:
                        self.logger.log_error_with_context(e, "Dynamic Mapping")
                    if self.graceful_degradation:
                        print(f"⚠️  {error_msg}. Using fallback mapping.")
                        mapped_data = None
                    else:
                        raise Exception(error_msg) from e
            else:
                print("⚠️  [PIPELINE] Dynamic mapper not available or no template")
            
            # Step 6: Semantic Validation (AI-driven)
            error_context["step"] = "Semantic Validation"
            validation_result = {"valid": True, "errors": [], "warnings": []}
            if self.semantic_validator:
                print("✅ Step 6: Validating invoice data using AI...")
                try:
                    timeout_guard.check()
                    validation_result = self.semantic_validator.validate_invoice(
                        canonical,
                        document_text
                    )
                    if not validation_result.get("valid", True):
                        print(f"⚠️  Validation found {len(validation_result.get('errors', []))} errors:")
                        for error in validation_result.get("errors", []):
                            print(f"   - {error}")
                except Exception as e:
                    print(f"⚠️  Validation error: {str(e)}. Continuing without validation.")
                    validation_result = {"valid": False, "errors": [f"Validation failed: {str(e)}"]}
            
            # Step 7: Export using template
            error_context["step"] = "Export"
            output_file = None
            if output_format in ["csv", "excel"]:
                if template is None:
                    # Use default template
                    template = self.template_parser.create_default_template()
                
                print(f"📊 Step 7: Exporting to {output_format.upper()}...")
                if output_path is None:
                    input_path = Path(file_path)
                    # Save CSV files to final_output directory
                    final_output_dir = "final_output"
                    Path(final_output_dir).mkdir(parents=True, exist_ok=True)
                    output_path = f"{final_output_dir}/{input_path.stem}_export.{output_format}"
                
                try:
                    # Use mapped_data if available, otherwise use canonical with template
                    print(f"🔍 [PIPELINE] Before export - mapped_data: {mapped_data}")
                    print(f"🔍 [PIPELINE] Before export - template: {template.get('name', 'Unknown')}")
                    
                    if mapped_data:
                        print("🔍 [PIPELINE] Using mapped_data for export")
                        output_file = self.exporter.export_mapped_data_to_csv(
                            mapped_data, template, output_path
                        )
                    else:
                        print("🔍 [PIPELINE] Using canonical + template for export (fallback)")
                        output_file = self.exporter.export_to_csv(canonical, template, output_path)
                    print(f"✅ Exported to: {output_file}")
                except Exception as e:
                    print(f"❌ [PIPELINE] Export error: {str(e)}")
                    import traceback
                    print(f"❌ [PIPELINE] Export traceback: {traceback.format_exc()}")
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
                "mapped_data": mapped_data,  # Include mapped_data for consolidation
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
