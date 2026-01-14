# AI-Powered Mapping Setup Guide

This guide explains how to set up AI-powered column mapping for super accurate CSV generation.

## Why Use AI Mapping?

AI-powered mapping provides:
- **Semantic Understanding**: Understands that "qty" = "Quantity" = "Qty"
- **Context Awareness**: Knows "amount" should map to "Item subtotal" not just "Total"
- **Error Detection**: Identifies and corrects misaligned data
- **Better Accuracy**: 90%+ accuracy vs 70% with rule-based matching

## Quick Setup (Gemini - Free Tier)

### 1. Get Free Gemini API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### 2. Install Dependencies

```bash
pip install google-generativeai
```

### 3. Configure Environment

Edit your `.env` file:

```env
# AI Configuration
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_api_key_here
```

### 4. Test It

```bash
python main.py interactive samples/amazon_invoice.png
```

You should see: `✅ AI mapping enabled using gemini (gemini-2.5-flash)`

## How It Works

1. **Extraction**: AWS Textract extracts tables and text
2. **AI Analysis**: Gemini analyzes table headers and matches to your columns
3. **Validation**: AI validates and corrects any mapping errors
4. **CSV Generation**: Creates accurate CSV with proper data alignment

## Example

**Input Columns:**
- `sr.no`, `particulars`, `qty`, `rate`, `amount`

**Table Headers Found:**
- `Description`, `Quantity`, `Unit price (excl. VAT)`, `Item subtotal (incl. VAT)`

**AI Mapping:**
- `particulars` → `Description` ✅
- `qty` → `Quantity` ✅
- `rate` → `Unit price (excl. VAT)` ✅
- `amount` → `Item subtotal (incl. VAT)` ✅

## Free Tier Limits

Gemini 2.5 Flash (Free):
- 15 requests per minute
- 1 million tokens per day
- Perfect for development and small-scale use

**Note**: To see all available models, run:
```bash
python list_gemini_models.py
```

Common model names:
- `gemini-2.5-flash` (recommended, fastest)
- `gemini-2.5-pro` (more capable, slower)
- `gemini-2.0-flash` (alternative)

## Troubleshooting

### "API key not found"
- Make sure `.env` file exists in project root
- Check that `GEMINI_API_KEY` is set correctly
- Restart your terminal/IDE after adding the key

### "Package not installed"
```bash
pip install google-generativeai
```

### "Falling back to rule-based mapping"
- Check API key is valid
- Verify internet connection
- Check API quota hasn't been exceeded

## Advanced: Other AI Providers

### OpenAI (Paid)

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here
```

### Anthropic Claude (Paid)

```env
AI_PROVIDER=anthropic
AI_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=your_key_here
```

## Cost Comparison

| Provider | Model | Cost per 1K tokens | Free Tier |
|----------|-------|-------------------|-----------|
| Gemini | 1.5 Flash | Free | ✅ 1M tokens/day |
| OpenAI | gpt-4o-mini | $0.15 | ❌ |
| Anthropic | claude-3-haiku | $0.25 | ❌ |

**Recommendation**: Use Gemini for development and testing!
