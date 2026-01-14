# InvoiceToExcel v2.0 - Document Text Extraction & CSV Conversion

A scalable, modular tool that extracts text and structured data from documents (PDFs, images) using AWS Textract and converts them to CSV format with intelligent column mapping.

## 🚀 Features

- **📄 Multi-format Support**: PDF, PNG, JPG, JPEG
- **🔍 AWS Textract Integration**: Advanced text extraction with high accuracy
- **🎯 Intelligent Column Mapping**: Smart data matching to user-defined columns
- **🤖 AI-Powered Normalization**: 4-layer normalization pipeline with Gemini AI
- **📊 Audit-Ready CSV Output**: Professional CSV format ready for accounting/auditing
- **📊 Interactive CSV Creation**: User-friendly column configuration
- **🏗️ Modular Architecture**: Scalable, maintainable codebase
- **🔧 Multiple Interfaces**: CLI and interactive modes
- **🔄 Batch Processing**: Process multiple invoices at once

## 📁 Project Structure

```
InvoiceToExcel/
├── src/
│   ├── core/                    # Core business logic
│   │   ├── extraction/          # Document extraction layer
│   │   │   ├── textract_client.py
│   │   │   └── document_processor.py
│   │   ├── normalization/       # 4-layer normalization pipeline
│   │   │   ├── normalization_pipeline.py
│   │   │   ├── deterministic_mapper.py    # Layer A
│   │   │   ├── ai_semantic_resolver.py    # Layer B (AI)
│   │   │   ├── validation_engine.py       # Layer C
│   │   │   ├── ai_repair.py               # Layer D (AI)
│   │   │   ├── canonical_schema.py
│   │   │   ├── confidence_engine.py
│   │   │   └── benchmarking.py
│   │   ├── mapping/             # CSV mapping layer
│   │   │   ├── csv_mapper.py
│   │   │   ├── professional_csv_mapper.py
│   │   │   └── ai_mapper.py
│   │   └── export/              # Export functionality
│   │       └── csv_exporter.py
│   ├── interfaces/              # User interfaces
│   │   ├── cli.py
│   │   └── interactive_csv.py
│   ├── models/                  # Data models
│   │   ├── document.py
│   │   ├── extraction_result.py
│   │   └── csv_config.py
│   └── utils/                   # Utilities
│       ├── file_utils.py
│       ├── config.py
│       └── logger.py
├── config/                      # Configuration
│   ├── settings.py
│   └── field_mappings.json
├── scripts/                     # Utility scripts
│   ├── setup_ai.py              # AI setup verification
│   └── list_gemini_models.py    # List available AI models
├── tests/                       # Test files
│   └── test_normalization_pipeline.py
├── docs/                        # Documentation
├── samples/                     # Sample documents
├── output/                      # Generated files
├── batch_csv_generator.py       # Batch processing script
├── main.py                      # Main entry point
├── requirements.txt
└── README.md
```

## 🛠️ Installation

### Prerequisites
- Python 3.7+
- AWS Account with Textract access
- AWS credentials configured
- Google Gemini API key (for AI-powered normalization) - Free tier available

### Setup
```bash
# Clone repository
git clone https://github.com/anishghanwat/InvoiceToExcel.git
cd InvoiceToExcel

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.template .env
# Edit .env with your AWS credentials and Gemini API key

# Verify AI setup (optional)
python scripts/setup_ai.py
```

## 🎯 Usage

### Main Entry Point
```bash
# Show help
python main.py help

# Simple extraction (CLI mode)
python main.py cli document.pdf

# Interactive CSV creation
python main.py interactive document.pdf
```

### Alternative Usage
```bash
# Direct CLI access
python -m src.interfaces.cli document.pdf

# Direct interactive access  
python -m src.interfaces.interactive_csv document.pdf
```

### Python API
```python
from src.core.extraction.document_processor import DocumentProcessor
from src.core.mapping.csv_mapper import CSVMapper

# Extract data
processor = DocumentProcessor()
results = processor.process_document("invoice.pdf")

# Create CSV mapping
mapper = CSVMapper()
categorized_data = mapper.analyze_extracted_data(results)
columns = ["sr.no", "particulars", "amount"]
mappings = mapper.map_columns_to_data(columns, categorized_data)
csv_path = mapper.create_csv_output(columns, mappings, "output.csv")
```

## 🔧 Configuration

### AWS Setup
1. **Create AWS Account** at https://aws.amazon.com
2. **Enable Textract Service** in your region
3. **Create IAM User** with `AmazonTextractFullAccess` policy
4. **Generate Access Keys** and add to `.env`:

```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
```

### Application Settings
Edit `config/settings.py` for:
- File size limits
- Confidence thresholds  
- Output formats
- Logging levels

### AI Configuration
Edit `.env` file for AI settings:
```env
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_api_key_here
```

Get free Gemini API key: https://makersuite.google.com/app/apikey

## 📊 Data Flow

```
Document Input
     ↓
[Extraction Layer] → Raw extracted data (text, tables, key-value pairs)
     ↓
[Normalization Pipeline] → Canonical JSON format
     ├── Layer A: Deterministic Mapping (rules-based)
     ├── Layer B: AI Semantic Resolution (Gemini AI)
     ├── Layer C: Validation & Confidence Scoring
     └── Layer D: AI Repair (conditional AI correction)
     ↓
[Mapping Layer] → Column-mapped data  
     ↓
[Export Layer] → Audit-ready CSV output
```

## 🧪 Testing

```bash
# Test normalization pipeline
python tests/test_normalization_pipeline.py

# Test with sample document
python main.py interactive "samples/husco 28 invoice.pdf"

# Batch process all samples
python batch_csv_generator.py
```

## 📈 Output Examples

### Extraction Results
- `filename_results.json` - Clean, structured data
- `filename_raw_textract.json` - Complete AWS response
- `filename_extracted_text.txt` - Human-readable text

### CSV Output
```csv
sr.no,particulars,rate,amount
28,Invoice Header,1000.00,1000.00
S22811,Product Description,2000.00,2000.00
1,Line Item Details,275.00,275.00
```

## 🔮 Roadmap

### Phase 1: ✅ Extraction & Mapping (Completed)
- AWS Textract integration
- Intelligent column mapping
- Interactive CSV creation

### Phase 2: ✅ Normalization Pipeline (Completed)
- 4-layer normalization architecture
- AI-powered semantic resolution
- Deterministic validation
- Confidence scoring
- AI-powered repair

### Phase 3: 🚧 Advanced Features (In Progress)
- Batch processing ✅
- Audit-ready CSV output ✅
- Enhanced table extraction ✅

### Phase 4: 🔄 Future Enhancements
- Web interface
- Template learning
- API endpoints
- Multi-language support
- Integration with accounting software

## 💰 AWS Costs

- **Textract Pricing**: ~$1.50 per 1,000 pages
- **Free Tier**: 1,000 pages/month for 3 months (new accounts)
- **Example**: 100 invoices ≈ $0.15

## 🛡️ Error Handling

- **File Validation**: Format and size checks
- **AWS Integration**: Credential and API error handling
- **Data Processing**: Graceful handling of extraction failures
- **User Input**: Validation and helpful error messages

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues
- **AWS Credentials**: Ensure `.env` file has correct credentials
- **AI API Key**: Set `GEMINI_API_KEY` in `.env` file for AI features
- **File Format**: Only PDF, PNG, JPG, JPEG supported
- **File Size**: Maximum 10MB per document
- **Permissions**: IAM user needs Textract access

### Getting Help
1. Check [AWS Setup Guide](docs/AWS_SETUP_GUIDE.md)
2. Check [AI Setup Guide](docs/AI_SETUP.md)
3. Review [Project Structure](docs/PROJECT_STRUCTURE.md)
4. Run `python scripts/setup_ai.py` to verify AI setup
5. Open GitHub issue for bugs/features

## 🎉 Success Stories

This tool successfully processes:
- ✅ Standard invoices and receipts
- ✅ Multi-column tabular data
- ✅ Mixed text and numeric content
- ✅ Various document layouts
- ✅ Scanned and digital documents

---

**Ready to extract data from your documents?** 
```bash
python main.py interactive your_invoice.pdf
```