# Production Readiness Implementation

This document outlines the production-ready features implemented for the InvoiceToExcel application.

## ✅ Completed Features

### 1. Retry Logic with Exponential Backoff

**Location**: `src/utils/retry.py`

- **Textract API Retries**: Automatic retry with exponential backoff for transient AWS errors
- **Intelligent Error Detection**: Distinguishes between retryable (5xx, throttling) and non-retryable (4xx, invalid input) errors
- **Configurable Parameters**: 
  - Max retries: `TEXTRACT_MAX_RETRIES` (default: 3)
  - Initial delay: `TEXTRACT_RETRY_INITIAL_DELAY` (default: 1.0s)
  - Max delay: `TEXTRACT_RETRY_MAX_DELAY` (default: 60.0s)
- **Jitter**: Random jitter added to prevent thundering herd problem

**Usage**:
```python
from src.utils.retry import retry_aws_operation

result = retry_aws_operation(
    lambda: textract_client.analyze_document(bytes),
    max_retries=3,
    on_retry=lambda attempt, error: print(f"Retry {attempt}...")
)
```

### 2. Comprehensive Error Handling

**Location**: `src/core/pipeline.py`, `src/core/extraction/textract_client.py`, `src/core/ai/canonical_fixer.py`

- **Context-Aware Errors**: All errors include step context and file information
- **Error Propagation**: Proper exception chaining with `from e` for debugging
- **Specific Exception Types**: 
  - `FileNotFoundError` for missing files
  - `ValueError` for invalid input
  - `TimeoutError` for timeouts
  - `NonRetryableError` for errors that shouldn't be retried
- **Graceful Degradation**: AI failures don't crash the pipeline (configurable)

**Error Context Example**:
```python
error_context = {"step": "Textract Extraction", "file": "invoice.pdf"}
# Errors include this context for debugging
```

### 3. Structured Logging

**Location**: `src/utils/logger.py`

- **Structured Context**: Logs include operation context (file, step, duration)
- **Performance Metrics**: Automatic logging of operation durations
- **Log Levels**: Info, Debug, Warning, Error, Critical
- **File Logging**: Automatic log file creation with timestamps
- **Context Logging**: `log_with_context()` for structured data

**Usage**:
```python
logger.log_performance("Textract Extraction", 1234.56, {"file": "invoice.pdf"})
logger.log_with_context('error', 'Processing failed', {"step": "Canonical Building"})
```

### 4. Configuration Management

**Location**: `config/settings.py`

- **Environment Variable Support**: All settings can be overridden via environment variables
- **Production Defaults**: Sensible defaults for production use
- **Feature Flags**: Enable/disable features via configuration
- **Centralized Settings**: Single source of truth for all configuration

**Key Settings**:
- `PIPELINE_TIMEOUT_SECONDS`: Maximum processing time (default: 300s)
- `TEXTRACT_MAX_RETRIES`: Retry attempts for Textract (default: 3)
- `AI_MAX_RETRIES`: Retry attempts for AI calls (default: 2)
- `ENABLE_GRACEFUL_DEGRADATION`: Continue on non-critical failures (default: true)
- `ENABLE_STRUCTURED_LOGGING`: Enable structured logging (default: true)

**Environment Variables**:
```bash
export PIPELINE_TIMEOUT_SECONDS=600
export TEXTRACT_MAX_RETRIES=5
export ENABLE_AI_FIXING=false
```

### 5. Timeout Handling

**Location**: `src/utils/timeout.py`, `src/core/pipeline.py`

- **Pipeline Timeout**: Overall pipeline timeout (default: 5 minutes)
- **Timeout Guards**: Check elapsed time during long operations
- **Cross-Platform**: Works on both Unix (signal-based) and Windows (polling)
- **Timeout Context Manager**: `with timeout_context(30.0): ...`

**Usage**:
```python
timeout_guard = TimeoutGuard(300.0)  # 5 minutes
timeout_guard.check()  # Raises TimeoutError if exceeded
```

### 6. Graceful Degradation

**Location**: `src/core/pipeline.py`

- **AI Failure Handling**: Pipeline continues if AI fixing fails (configurable)
- **Validation Errors**: Non-blocking validation errors
- **Service Unavailability**: Continues processing with available services
- **Partial Results**: Returns partial results even if some steps fail

**Configuration**:
```python
# In .env or settings.py
ENABLE_GRACEFUL_DEGRADATION=true  # Continue on non-critical failures
```

### 7. Input Validation and Sanitization

**Location**: `src/core/extraction/document_processor.py`

- **File Existence**: Checks file exists and is readable
- **File Type Validation**: Validates supported formats (.pdf, .png, .jpg, .jpeg)
- **File Size Validation**: Enforces maximum file size (10MB default)
- **Empty File Detection**: Rejects empty files
- **Path Validation**: Ensures path is a file, not a directory
- **Specific Exceptions**: Uses `FileNotFoundError` and `ValueError` for clarity

**Validation Checks**:
- ✅ File exists
- ✅ File is readable
- ✅ File is not empty
- ✅ File size within limits
- ✅ Supported file format
- ✅ Path is a file (not directory)

## Architecture Improvements

### Error Handling Flow

```
Pipeline Start
    ↓
Input Validation (FileNotFoundError, ValueError)
    ↓
Textract Extraction (with retries)
    ↓
Canonical Building (with timeout checks)
    ↓
AI Fixing (with graceful degradation)
    ↓
Validation (non-blocking)
    ↓
Export (with error context)
    ↓
Return Results (with success flag)
```

### Retry Strategy

1. **Transient Errors**: Automatically retried (5xx, throttling)
2. **Permanent Errors**: Fail immediately (4xx, invalid input)
3. **Exponential Backoff**: 1s → 2s → 4s → ... (max 60s)
4. **Jitter**: Random variation to prevent synchronized retries

### Logging Strategy

- **Structured Logs**: JSON-like context in log messages
- **Performance Tracking**: Automatic duration logging
- **Error Context**: Errors include step and file information
- **Log Levels**: Appropriate levels for different scenarios

## Configuration Examples

### Production Configuration

```bash
# .env file
PIPELINE_TIMEOUT_SECONDS=600
TEXTRACT_MAX_RETRIES=5
TEXTRACT_RETRY_INITIAL_DELAY=2.0
TEXTRACT_RETRY_MAX_DELAY=120.0
AI_MAX_RETRIES=3
ENABLE_GRACEFUL_DEGRADATION=true
ENABLE_STRUCTURED_LOGGING=true
LOG_LEVEL=INFO
```

### Development Configuration

```bash
# .env file
PIPELINE_TIMEOUT_SECONDS=300
TEXTRACT_MAX_RETRIES=2
ENABLE_GRACEFUL_DEGRADATION=false  # Fail fast for debugging
ENABLE_STRUCTURED_LOGGING=true
LOG_LEVEL=DEBUG
```

## Testing Production Features

### Test Retry Logic

```python
# Simulate transient error
from src.utils.retry import retry_aws_operation
from botocore.exceptions import ClientError

def test_retry():
    attempt = 0
    def failing_operation():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise ClientError({'Error': {'Code': 'ThrottlingException'}}, 'operation')
        return "success"
    
    result = retry_aws_operation(failing_operation, max_retries=3)
    assert result == "success"
```

### Test Timeout

```python
from src.utils.timeout import TimeoutGuard, TimeoutError

def test_timeout():
    guard = TimeoutGuard(1.0)  # 1 second timeout
    time.sleep(2)  # Exceed timeout
    guard.check()  # Raises TimeoutError
```

### Test Error Handling

```python
from src.core.pipeline import InvoiceProcessingPipeline

pipeline = InvoiceProcessingPipeline(enable_logging=True)
try:
    result = pipeline.process_invoice("nonexistent.pdf")
except FileNotFoundError as e:
    # Proper error type
    assert "not found" in str(e).lower()
```

## Monitoring and Observability

### Log Analysis

Logs include:
- Operation durations (performance metrics)
- Error context (step, file, error type)
- Retry attempts (with error codes)
- Timeout events

### Metrics to Track

1. **Success Rate**: `success: true/false` in results
2. **Processing Time**: `processing_time_ms` in metadata
3. **Retry Count**: Logged retry attempts
4. **Error Types**: Categorized by exception type
5. **Timeout Events**: TimeoutError occurrences

## Next Steps

1. **Metrics Collection**: Add metrics export (Prometheus, CloudWatch)
2. **Alerting**: Set up alerts for high error rates
3. **Circuit Breaker**: Add circuit breaker pattern for external services
4. **Rate Limiting**: Add rate limiting for API calls
5. **Health Checks**: Add health check endpoints
6. **Distributed Tracing**: Add tracing for distributed systems

## Summary

The application now includes:
- ✅ Retry logic with exponential backoff
- ✅ Comprehensive error handling
- ✅ Structured logging with context
- ✅ Configuration management
- ✅ Timeout handling
- ✅ Graceful degradation
- ✅ Input validation

All features are production-ready and configurable via environment variables.
