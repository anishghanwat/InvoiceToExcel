# New AI-Driven Architecture

## Overview

The system has been completely refactored to use AI-driven semantic understanding instead of hardcoded keyword matching. This makes it flexible, scalable, and future-proof.

## Key Changes

### ✅ Removed Hardcoded Logic
- **Before**: Keyword matching for field extraction (e.g., `if 'rate' in header_lower`)
- **After**: AI semantic understanding (understands meaning, not keywords)

### ✅ New AI Components

1. **AIClient** (`src/core/ai/ai_client.py`)
   - Unified interface for OpenAI (primary) and Gemini (fallback)
   - Handles API calls, retries, and error handling

2. **SemanticExtractor** (`src/core/ai/semantic_extractor.py`)
   - Extracts ALL invoice fields using AI semantic understanding
   - Replaces hardcoded keyword matching in `canonical_builder.py`
   - Understands variations (Rate/Unit Price/Cost = unit_price)

3. **SchemaInferencer** (`src/core/ai/schema_inferencer.py`)
   - Infers template schema from CSV headers
   - Understands column meanings, data types, formats
   - Maps to canonical model semantically

4. **DynamicMapper** (`src/core/ai/dynamic_mapper.py`)
   - Maps canonical invoice data to template columns
   - Handles missing fields intelligently
   - Transforms data types/formats as needed

5. **SemanticValidator** (`src/core/ai/semantic_validator.py`)
   - Validates invoice data using AI semantic understanding
   - Checks for logical inconsistencies
   - No hardcoded business rules

6. **LearningEngine** (`src/core/ai/learning_engine.py`)
   - Learns from user corrections
   - Stores mapping patterns
   - Improves over time

### ✅ Simplified Components

1. **CanonicalBuilder** (`src/core/normalize/canonical_builder.py`)
   - **Before**: 1000+ lines of hardcoded extraction logic
   - **After**: ~50 lines - just creates empty structure
   - Extraction now done by SemanticExtractor

2. **TemplateParser** (`src/core/templates/template_parser.py`)
   - Now uses SchemaInferencer for CSV header mapping
   - Removed hardcoded keyword matching

3. **Pipeline** (`src/core/pipeline.py`)
   - Updated to use new AI-driven flow
   - Steps: Textract → Semantic Extraction → Schema Inference → Dynamic Mapping → Validation → Export

## New Flow

```
1. User uploads template (CSV with any column names)
   ↓
2. Schema Inferencer (AI) - understands template structure
   ↓
3. User uploads invoice PDFs
   ↓
4. AWS Textract - extracts raw signals (text, tables, kv-pairs)
   ↓
5. Semantic Extractor (AI) - extracts ALL invoice fields semantically
   ↓
6. Dynamic Mapper (AI) - maps canonical data to template columns
   ↓
7. Semantic Validator (AI) - validates data
   ↓
8. CSV Export - writes mapped data
   ↓
9. Learning Engine - stores patterns for future use
```

## Benefits

1. **Zero Hardcoding** - All logic is AI-driven
2. **Handles Any Template** - No assumptions about column names
3. **Improves Over Time** - Learning engine stores patterns
4. **Scalable** - Works for many users with different templates
5. **Future-Proof** - Adapts to new formats automatically

## Files Changed

### New Files
- `src/core/ai/ai_client.py`
- `src/core/ai/semantic_extractor.py`
- `src/core/ai/schema_inferencer.py`
- `src/core/ai/dynamic_mapper.py`
- `src/core/ai/semantic_validator.py`
- `src/core/ai/learning_engine.py`
- `prompts/extraction_prompt.txt`
- `prompts/schema_inference_prompt.txt`
- `prompts/mapping_prompt.txt`
- `prompts/validation_prompt.txt`

### Modified Files
- `src/core/normalize/canonical_builder.py` - Simplified (removed hardcoded logic)
- `src/core/pipeline.py` - Updated to use new AI flow
- `src/core/templates/template_parser.py` - Uses SchemaInferencer
- `src/core/templates/exporter.py` - Added export_mapped_data_to_csv method
- `src/core/ai/__init__.py` - Exports new classes

### Deprecated (Still Available for Backward Compatibility)
- `src/core/ai/canonical_fixer.py` - Old AI fixer (replaced by SemanticExtractor)

## Usage

The system works the same way from user perspective:

```python
from src.core.pipeline import InvoiceProcessingPipeline

pipeline = InvoiceProcessingPipeline(use_ai=True)

result = pipeline.process_invoice(
    file_path='invoice.pdf',
    template=template,  # CSV template or JSON template
    output_format='csv'
)
```

But now:
- Template can have ANY column names
- AI understands semantics, not keywords
- System learns and improves over time

## Configuration

AI providers are auto-detected from environment variables:
- `OPENAI_API_KEY` - Primary provider
- `GEMINI_API_KEY` - Fallback provider

The system automatically uses OpenAI if available, falls back to Gemini if OpenAI fails.
