# Testing and Validation Guide

## Overview

This document describes the comprehensive testing framework for the Invoice Processing System. The framework includes unit tests, integration tests, validation tests, and batch testing capabilities.

## Test Structure

### 1. Unit Tests (`tests/test_canonical_builder.py`)

Tests individual extraction methods and edge cases:
- Invoice header extraction
- Buyer information extraction
- Total and tax extraction
- Amount and percentage normalization
- Edge cases (Bank Ref No., combined fields, etc.)

**Example:**
```python
def test_extract_buyer_info_skips_bank_ref(builder):
    """Test that buyer extraction skips 'Bank Ref No.' fields."""
    results = {
        "key_value_pairs": [
            {"key": "Bank Ref No.", "value": "REF123"},
            {"key": "To,", "value": "HDFC Bank Ltd."},
        ]
    }
    buyer = builder._extract_buyer_info(results)
    assert buyer["name"] == "HDFC Bank Ltd."
```

### 2. Integration Tests (`tests/test_pipeline_integration.py`)

Tests the complete pipeline flow:
- Full pipeline processing
- Template handling
- Error handling
- Output file generation

**Requirements:** AWS credentials

### 3. Validation Tests (`tests/test_validation.py`)

Tests validation rules:
- GSTIN format validation
- Mathematical consistency (totals match line items)
- Tax calculation validation
- Data quality checks

### 4. Batch Tests (`tests/test_multiple_invoices.py`)

Tests extraction across multiple invoice formats:
- Processes all sample invoices
- Generates extraction statistics
- Identifies format-specific issues
- Reports success rates

**Requirements:** AWS credentials, sample invoices in `samples/` directory

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run specific test suite
python run_tests.py unit
python run_tests.py integration
python run_tests.py validation
python run_tests.py batch
```

### Using Pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_canonical_builder.py -v

# Run specific test
pytest tests/test_canonical_builder.py::TestCanonicalBuilder::test_extract_invoice_header -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Test Coverage

### Current Coverage Areas

✅ **Extraction Logic**
- Invoice header fields (number, date, etc.)
- Buyer information (name, GSTIN, address)
- Seller information
- Line items
- Totals and taxes (CGST, SGST, IGST)
- Edge cases (Bank Ref No., combined fields)

✅ **Normalization**
- Amount parsing (commas, decimals)
- Percentage extraction
- Date formatting
- GSTIN validation

✅ **Pipeline Integration**
- Complete flow testing
- Template handling
- Error handling

✅ **Validation**
- GSTIN format
- Mathematical consistency
- Tax logic

### Areas for Expansion

- [ ] More edge cases for different invoice formats
- [ ] Performance testing
- [ ] AI fix accuracy testing
- [ ] Template export validation
- [ ] Error recovery testing

## Adding New Tests

### Unit Test Template

```python
def test_new_feature(builder):
    """Test description."""
    # Setup
    results = {
        "key_value_pairs": [...]
    }
    
    # Execute
    result = builder._extract_something(results)
    
    # Assert
    assert result == expected_value
```

### Integration Test Template

```python
@pytest.mark.skipif(
    not os.getenv('AWS_ACCESS_KEY_ID'),
    reason="AWS credentials not configured"
)
def test_new_integration(pipeline, sample_invoice_path):
    """Test complete pipeline with new feature."""
    result = pipeline.process_invoice(sample_invoice_path)
    assert result["canonical"] is not None
```

## Test Data

### Sample Invoices

Place test invoices in the `samples/` directory:
- `.pdf` files
- `.png` files
- `.jpg` files

### Mock Data

For unit tests, use mock Textract results:
```python
sample_textract_results = {
    "key_value_pairs": [...],
    "tables": [...],
    "text_blocks": [...]
}
```

## Continuous Integration

Tests are designed to be CI-friendly:
- Unit tests run fast without external dependencies
- Integration tests are marked and can be skipped
- Batch tests provide detailed reporting

### CI Configuration Example

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src
```

## Best Practices

1. **Write tests first** for new features (TDD)
2. **Test edge cases** (empty values, malformed data, etc.)
3. **Keep tests fast** - unit tests should run in milliseconds
4. **Use fixtures** for common setup
5. **Mark slow tests** with `@pytest.mark.slow`
6. **Skip tests** that require external services when credentials aren't available

## Troubleshooting

### Tests Failing

1. Check AWS credentials are set (for integration tests)
2. Verify sample invoices exist in `samples/` directory
3. Check Python version compatibility
4. Review test output for specific error messages

### Coverage Issues

1. Run with `--cov=src` to see coverage report
2. Add tests for uncovered code paths
3. Use `--cov-report=html` for detailed HTML report

## Next Steps

1. **Expand test coverage** for edge cases
2. **Add performance benchmarks** for large invoices
3. **Create regression test suite** with known good/bad invoices
4. **Add visual regression tests** for template exports
5. **Implement test data management** for consistent testing
