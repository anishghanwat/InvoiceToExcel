# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set Up AWS Credentials

### Option A: Environment File (Recommended)
```bash
# Copy the template
cp .env.example .env

# Edit .env file with your credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
```

### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_REGION=us-east-1
```

## 3. Process a Document

### CLI Usage
```bash
# Process any PDF or image file
python -m src.cli your_document.pdf
```

### Python Script Usage
```python
from src.document_processor import DocumentProcessor

processor = DocumentProcessor()
results = processor.process_document("your_document.pdf")
print(f"Extracted {len(results['text_blocks'])} text blocks")
```

## 4. Check Results

The tool creates an `output` directory with:
- `filename_results.json` - Structured data
- `filename_raw_textract.json` - Raw AWS response  
- `filename_extracted_text.txt` - Human-readable text

## AWS Setup (First Time Only)

### 1. Create AWS Account
- Go to https://aws.amazon.com
- Sign up for an account

### 2. Create IAM User
1. AWS Console → IAM → Users → Create user
2. Username: `textract-user`
3. Attach policy: `AmazonTextractFullAccess`
4. Create user

### 3. Get API Keys
1. Click on your user → Security credentials
2. Create access key → Application running outside AWS
3. Copy Access Key ID and Secret Access Key
4. Add them to your `.env` file

## Test with Sample File

```bash
# Download a sample invoice or use any PDF/image
python -m src.cli sample_invoice.pdf

# Check the output directory for results
ls output/
```

That's it! You're ready to extract text from documents using AWS Textract.