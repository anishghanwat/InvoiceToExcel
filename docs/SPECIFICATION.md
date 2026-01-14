# Invoice to CSV/Excel Conversion Tool - Specification

## 1. Exact Problem This Tool Solves

### Problem Statement
Accounting teams and small businesses struggle to extract structured data from invoices, receipts, and statements that arrive in various formats (PDFs, scanned images, photos). Manual data entry is:
- **Time-consuming**: Hours spent typing invoice details into spreadsheets
- **Error-prone**: Human mistakes in transcription
- **Inconsistent**: Different people format data differently
- **Not scalable**: Volume increases make manual processing impractical

### Solution
An automated tool that:
- Accepts PDF or image files (scanned/photographed invoices)
- Extracts key financial data using AWS Textract
- Normalizes and validates extracted data
- Provides a review interface for human verification
- Exports clean, structured CSV/Excel files ready for accounting systems

### Target Users
- Small business owners managing expenses
- Accounting teams processing vendor invoices
- Bookkeepers digitizing paper records
- Finance departments automating data entry

---

## 2. Minimal Feature Set for MVP

### Core Features (Must Have)

#### 2.1 Document Upload
- **Input**: PDF, PNG, JPG, JPEG files
- **Validation**: File type, size limits (max 10MB), basic format checks
- **Storage**: Temporary storage for processing

#### 2.2 Text Extraction (AWS Textract)
- **Service**: AWS Textract AnalyzeDocument API
- **Mode**: Forms and Tables detection
- **Output**: Raw extraction results (key-value pairs, tables, text)

#### 2.3 Data Normalization
- **Canonical JSON Schema**: Standardized structure for all invoices
- **Field Mapping**: Map Textract results to standard fields
- **AI Repair**: Fix common OCR errors (date formats, numbers, vendor names)
- **Validation**: Check data types, formats, required fields

#### 2.4 Confidence Scoring
- **Per-field confidence**: Score each extracted field (0-100%)
- **Overall document confidence**: Aggregate score
- **Flag low-confidence fields**: Highlight uncertain extractions

#### 2.5 Review Interface
- **Display extracted data**: Show all fields in editable form
- **Visual document preview**: Show original document alongside data
- **Edit capability**: Allow manual corrections
- **Confidence indicators**: Visual cues for low-confidence fields

#### 2.6 Export
- **CSV export**: Standard comma-separated values
- **Excel export**: .xlsx format with formatting
- **Column structure**: Date, Invoice Number, Vendor, Line Items, Quantities, Tax, Total

### Nice-to-Have (Post-MVP)
- Batch processing (multiple files)
- Custom field mapping
- Template learning (remember vendor formats)
- API access
- Integration with accounting software

---

## 3. Ideal Input → Output Flow

### Detailed Flow Diagram

```
┌─────────────────┐
│  User Uploads   │
│  PDF/Image      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  File Validation│
│  - Type check   │
│  - Size limit   │
│  - Format OK?   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Textract   │
│  AnalyzeDocument│
│  - Forms        │
│  - Tables       │
│  - Raw text     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse Results  │
│  - Key-value    │
│  - Tables       │
│  - Text blocks  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Normalization  │
│  - Map fields   │
│  - AI Repair    │
│  - Validate     │
│  - Canonical    │
│    JSON         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Confidence     │
│  Scoring        │
│  - Per field    │
│  - Overall      │
│  - Flag issues  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Review UI      │
│  - Display data │
│  - Show preview │
│  - Edit fields  │
│  - Confidence   │
│    indicators   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  User Approval  │
│  - Review       │
│  - Edit         │
│  - Confirm      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Export         │
│  - CSV          │
│  - Excel        │
│  - Structured   │
└─────────────────┘
```

### Data Transformation Stages

#### Stage 1: Raw Textract Output
```json
{
  "Blocks": [...],
  "DocumentMetadata": {...},
  "Forms": [
    {
      "Key": {"Text": "Invoice Number", "Confidence": 95.5},
      "Value": {"Text": "INV-2024-001", "Confidence": 92.3}
    }
  ],
  "Tables": [...]
}
```

#### Stage 2: Parsed & Mapped
```json
{
  "invoice_number": "INV-2024-001",
  "date": "2024-01-15",
  "vendor": "Acme Corp",
  "line_items": [
    {"description": "Widget A", "quantity": 10, "unit_price": 25.00, "total": 250.00}
  ],
  "subtotal": 250.00,
  "tax": 20.00,
  "total": 270.00
}
```

#### Stage 3: Canonical JSON (Normalized)
```json
{
  "document_id": "doc_123",
  "extraction_metadata": {
    "source_file": "invoice.pdf",
    "extracted_at": "2024-01-20T10:30:00Z",
    "overall_confidence": 87.5
  },
  "invoice": {
    "invoice_number": {"value": "INV-2024-001", "confidence": 92.3, "source": "forms"},
    "date": {"value": "2024-01-15", "confidence": 95.1, "source": "forms", "normalized": true},
    "vendor": {"value": "Acme Corp", "confidence": 88.7, "source": "forms"},
    "line_items": [
      {
        "description": {"value": "Widget A", "confidence": 90.2},
        "quantity": {"value": 10, "confidence": 95.0},
        "unit_price": {"value": 25.00, "confidence": 93.1},
        "total": {"value": 250.00, "confidence": 94.5}
      }
    ],
    "subtotal": {"value": 250.00, "confidence": 96.2},
    "tax": {"value": 20.00, "confidence": 89.3},
    "tax_rate": {"value": 8.0, "confidence": 85.0},
    "total": {"value": 270.00, "confidence": 97.8}
  },
  "confidence_scores": {
    "critical_fields": {
      "invoice_number": 92.3,
      "date": 95.1,
      "total": 97.8
    },
    "overall": 87.5
  },
  "validation": {
    "has_invoice_number": true,
    "has_date": true,
    "has_total": true,
    "line_items_count": 1,
    "math_checks": {
      "line_items_sum": true,
      "tax_calculation": true,
      "total_calculation": true
    }
  }
}
```

#### Stage 4: Final Export (CSV)
```csv
Date,Invoice Number,Vendor,Description,Quantity,Unit Price,Line Total,Tax,Total
2024-01-15,INV-2024-001,Acme Corp,Widget A,10,25.00,250.00,20.00,270.00
```

---

## 4. Clear Assumptions and Limitations

### Assumptions

#### 4.1 Document Quality
- **Assumption**: Documents are reasonably clear (not extremely blurry or damaged)
- **Reality**: OCR accuracy degrades with poor quality scans
- **Mitigation**: Confidence scoring flags low-quality extractions

#### 4.2 Document Language
- **Assumption**: Documents are in English
- **Reality**: Multi-language support requires additional configuration
- **Mitigation**: MVP focuses on English; can extend later

#### 4.3 Document Structure
- **Assumption**: Invoices follow common patterns (header with vendor/date, line items table, totals at bottom)
- **Reality**: Some invoices have non-standard layouts
- **Mitigation**: Flexible field mapping and manual review step

#### 4.4 Field Presence
- **Assumption**: Most invoices contain: date, invoice number, vendor, line items, total
- **Reality**: Some fields may be missing or in different locations
- **Mitigation**: Validation flags missing critical fields; user can fill manually

#### 4.5 AWS Textract Access
- **Assumption**: User has AWS account with Textract access
- **Reality**: Requires AWS credentials and billing setup
- **Mitigation**: Clear setup instructions; error handling for missing credentials

#### 4.6 File Formats
- **Assumption**: PDFs are text-based or high-quality scans (not pure images in PDF wrapper)
- **Reality**: Some PDFs are low-quality image scans
- **Mitigation**: Textract handles both, but quality varies

### Limitations

#### 4.7 Accuracy Limitations
- **OCR Errors**: Textract may misread characters (0 vs O, 1 vs I, etc.)
- **Layout Confusion**: Complex layouts may cause field misalignment
- **Handwriting**: Cannot process handwritten invoices
- **Mitigation**: Confidence scoring + human review step

#### 4.8 Processing Limitations
- **File Size**: Large files (>10MB) may timeout or be slow
- **Processing Time**: Textract API calls take 5-30 seconds per document
- **Cost**: AWS Textract charges per page processed
- **Mitigation**: File size limits, progress indicators, cost warnings

#### 4.9 Format Limitations
- **Multi-page**: Complex multi-page invoices may need special handling
- **Tables**: Nested or irregular tables may not extract perfectly
- **Currency**: Assumes USD; other currencies need configuration
- **Mitigation**: Manual review catches issues; can extend later

#### 4.10 Field Extraction Limitations
- **Vendor Names**: May extract partial names or include addresses
- **Dates**: Various date formats need normalization
- **Line Items**: Complex line items (discounts, taxes per item) may need manual adjustment
- **Mitigation**: AI repair attempts normalization; user can edit

#### 4.11 Technical Limitations
- **Single Document**: MVP processes one document at a time
- **No Learning**: Doesn't remember vendor-specific formats
- **No Templates**: Doesn't use pre-defined templates
- **Mitigation**: Post-MVP features can address these

### Error Handling Strategy

1. **File Upload Errors**: Clear error messages for invalid files
2. **Textract API Errors**: Retry logic, fallback to manual entry option
3. **Extraction Failures**: Flag document for manual review
4. **Validation Errors**: Highlight missing/invalid fields in UI
5. **Export Errors**: Provide alternative formats if one fails

---

## 5. Technical Architecture

### Technology Stack

#### Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI (REST API) or Flask (simpler MVP)
- **AWS SDK**: boto3 for Textract
- **Data Processing**: pandas for CSV/Excel export
- **Validation**: pydantic for data models

#### Frontend (Optional for MVP)
- **Simple Web UI**: HTML + JavaScript (vanilla or React)
- **File Upload**: Drag-and-drop interface
- **Review Interface**: Form with editable fields

#### Alternative: CLI Tool
- **Simple CLI**: Click or argparse
- **Interactive Review**: Terminal-based editing
- **Faster MVP**: No frontend needed

### Project Structure
```
InvoiceToExcelThree/
├── src/
│   ├── __init__.py
│   ├── upload.py          # File upload & validation
│   ├── textract_client.py # AWS Textract integration
│   ├── parser.py          # Parse Textract results
│   ├── normalizer.py      # Normalize & repair data
│   ├── confidence.py      # Confidence scoring
│   ├── validator.py       # Data validation
│   ├── exporter.py        # CSV/Excel export
│   └── models.py          # Data models (Pydantic)
├── tests/
│   └── test_*.py
├── requirements.txt
├── README.md
├── SPECIFICATION.md
└── .env.example
```

---

## 6. Success Criteria

### MVP Success Metrics
1. **Accuracy**: >85% of critical fields extracted correctly (with review)
2. **Speed**: Processing time <60 seconds per document
3. **Usability**: User can process an invoice in <5 minutes total
4. **Reliability**: Handles 80% of common invoice formats
5. **Export Quality**: CSV/Excel files import cleanly into accounting software

### Acceptance Criteria
- ✅ Upload PDF/image file
- ✅ Extract data using Textract
- ✅ Display extracted data with confidence scores
- ✅ Allow user to edit/correct data
- ✅ Export to CSV and Excel formats
- ✅ Handle errors gracefully
- ✅ Provide clear feedback throughout process

---

## Next Steps

1. Set up project structure
2. Implement core modules (upload, textract, parser, normalizer)
3. Build confidence scoring engine
4. Create review interface (CLI or web)
5. Implement export functionality
6. Add error handling and validation
7. Test with sample invoices
8. Document usage and setup
