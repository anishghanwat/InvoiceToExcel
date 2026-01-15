# Testing Guide

This directory contains comprehensive tests for the invoice processing system.

## Test Structure

- **`test_canonical_builder.py`**: Unit tests for extraction logic
- **`test_pipeline_integration.py`**: Integration tests for the complete pipeline
- **`test_validation.py`**: Validation rule tests
- **`test_multiple_invoices.py`**: Batch testing with multiple invoice samples
- **`conftest.py`**: Shared pytest fixtures and configuration

## Running Tests

### Run All Tests
```bash
python run_tests.py
# or
pytest tests/
```

### Run Specific Test Suites
```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# Validation tests only
python run_tests.py validation

# Batch tests with multiple invoices
python run_tests.py batch
```

### Run with Pytest Directly
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

## Test Requirements

### Unit Tests
- No external dependencies
- Fast execution
- Can run without AWS credentials

### Integration Tests
- Require AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- Require sample invoices in `samples/` directory
- May take longer to execute

### Batch Tests
- Require AWS credentials
- Test multiple invoice samples
- Generate extraction statistics

## Writing New Tests

### Unit Test Example
```python
def test_extract_invoice_number(builder):
    """Test invoice number extraction."""
    results = {
        "key_value_pairs": [
            {"key": "Invoice Number", "value": "INV-001"}
        ]
    }
    header = builder._extract_invoice_header(results)
    assert header["invoice_number"] == "INV-001"
```

### Integration Test Example
```python
@pytest.mark.skipif(
    not os.getenv('AWS_ACCESS_KEY_ID'),
    reason="AWS credentials not configured"
)
def test_full_pipeline(pipeline, sample_invoice_path):
    """Test complete pipeline."""
    result = pipeline.process_invoice(sample_invoice_path)
    assert result["canonical"] is not None
```

## Test Data

Place sample invoices in the `samples/` directory. Tests will automatically discover:
- `.pdf` files
- `.png` files
- `.jpg` files

## Continuous Integration

Tests are designed to be CI-friendly:
- Unit tests run quickly without external dependencies
- Integration tests are marked and can be skipped in CI
- Batch tests provide detailed reporting

## Coverage

To generate coverage reports:
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/index.html`.
