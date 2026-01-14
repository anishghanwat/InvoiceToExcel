"""
Complete Normalization Pipeline
Orchestrates all 4 layers: Deterministic → AI Semantic → Validation → AI Repair
"""
from typing import Dict, Any, Optional
from .deterministic_mapper import DeterministicMapper
from .ai_semantic_resolver import AISemanticResolver
from .validation_engine import ValidationEngine
from .ai_repair import AIRepair
from .canonical_schema import CanonicalSchema
from .confidence_engine import ConfidenceEngine
import os
import time


class NormalizationPipeline:
    """
    Complete normalization pipeline following the 4-layer architecture:
    A. Deterministic Mapping (rules)
    B. AI Semantic Interpretation (main AI)
    C. Confidence & Validation (rules)
    D. AI Repair (conditional AI)
    """
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize normalization pipeline.
        
        Args:
            use_ai: Whether to use AI layers (B and D)
        """
        # Layer A: Deterministic (always enabled)
        self.deterministic_mapper = DeterministicMapper()
        
        # Layer B: AI Semantic (optional)
        self.ai_resolver = None
        if use_ai:
            provider = os.getenv('AI_PROVIDER', 'gemini').lower()
            model = os.getenv('AI_MODEL')
            self.model = model
            try:
                self.ai_resolver = AISemanticResolver(provider=provider, model=model)
                if self.ai_resolver.client:
                    print(f"✅ AI Semantic Resolution enabled ({provider})")
            except Exception as e:
                print(f"⚠️  AI resolver initialization failed: {e}")
        
        # Layer C: Validation (always enabled)
        self.validator = ValidationEngine()
        
        # Layer D: AI Repair (optional, same as semantic resolver)
        self.ai_repair = None
        if use_ai and self.ai_resolver and self.ai_resolver.client:
            try:
                self.ai_repair = AIRepair(provider=provider, model=model)
            except Exception:
                pass
        
        # Confidence Engine (always enabled)
        self.confidence_engine = ConfidenceEngine()
    
    def normalize(self, results: Dict[str, Any], document_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete normalization pipeline following exact production architecture.
        
        Args:
            results: Textract extraction results
            document_text: Optional document text for AI context
            
        Returns:
            Canonical schema with confidence scores
        """
        start_time = time.time()
        ai_confidences = {}
        repair_confidences = {}
        
        # Layer A: Deterministic Mapping
        print("📋 Layer A: Deterministic Mapping...")
        canonical = self.deterministic_mapper.map_to_canonical(results)
        
        # Layer B: AI Semantic Resolution (if enabled and needed)
        if self.ai_resolver and self.ai_resolver.client:
            candidates = self.ai_resolver.collect_candidates(results)
            
            # Check if we have ambiguous fields (multiple candidates)
            ambiguous_fields = {k: v for k, v in candidates.items() if len(v) > 1}
            
            if ambiguous_fields:
                print(f"🧠 Layer B: AI Semantic Resolution ({len(ambiguous_fields)} ambiguous fields)...")
                # Get document context (first 500 chars of text)
                context = document_text or ' '.join([
                    block.get('text', '') for block in results.get('text_blocks', [])[:20]
                ])
                
                canonical, field_confidences = self.ai_resolver.resolve_ambiguous_fields(
                    canonical, 
                    ambiguous_fields,
                    context[:500] if context else None
                )
                ai_confidences.update(field_confidences)
            else:
                print("🧠 Layer B: AI Semantic Resolution (skipped - no ambiguous fields)")
        
        # Layer C: Validation
        print("✅ Layer C: Validation & Confidence Scoring...")
        validation_result = self.validator.validate(canonical)
        
        # Layer D: AI Repair (only if needed)
        if self.ai_repair and self.ai_repair.client and validation_result.get('needs_repair', False):
            print("🔧 Layer D: AI Repair...")
            document_text = document_text or ' '.join([
                block.get('text', '') for block in results.get('text_blocks', [])[:50]
            ])
            
            canonical, repair_conf = self.ai_repair.repair(
                canonical,
                validation_result,
                document_text[:1000] if document_text else None
            )
            repair_confidences.update(repair_conf)
            
            # Re-validate after repair
            validation_result = self.validator.validate(canonical)
        
        # Convert to canonical schema
        canonical_schema = CanonicalSchema.from_deterministic_mapping(canonical)
        
        # Calculate confidence scores
        field_confidences = self.confidence_engine.calculate_field_confidences(
            canonical,
            ai_confidences,
            validation_result,
            vendor_pattern_match=0.0  # TODO: Implement vendor pattern matching
        )
        
        overall_confidence = self.confidence_engine.calculate_overall_confidence(field_confidences)
        confidence_level = self.confidence_engine.get_confidence_level(overall_confidence)
        
        # Update canonical schema with confidence
        canonical_schema["confidence"]["overall"] = overall_confidence
        canonical_schema["confidence"]["fields"] = {
            "total_amount": field_confidences.get("total_amount", 0.0),
            "invoice_date": field_confidences.get("invoice_date", 0.0),
            "vendor_name": field_confidences.get("vendor", 0.0),
            "invoice_id": field_confidences.get("invoice_number", 0.0)
        }
        
        # Update metadata
        processing_time = int((time.time() - start_time) * 1000)
        canonical_schema["metadata"]["processing_time_ms"] = processing_time
        canonical_schema["metadata"]["ai_version"] = self.model if self.ai_resolver and self.ai_resolver.client else None
        
        # Return in format compatible with existing code
        return {
            'canonical': canonical,  # Legacy format for CSV generation
            'canonical_schema': canonical_schema,  # New canonical schema
            'validation': validation_result,
            'confidence': overall_confidence,
            'confidence_level': confidence_level,
            'field_confidences': field_confidences
        }
