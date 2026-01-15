"""
Retry utilities with exponential backoff for production-grade error handling.
"""
import time
import random
from typing import Callable, TypeVar, Optional, List, Tuple
from functools import wraps
from botocore.exceptions import ClientError

T = TypeVar('T')


class RetryableError(Exception):
    """Exception that indicates an operation should be retried."""
    pass


class NonRetryableError(Exception):
    """Exception that indicates an operation should not be retried."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Exception, ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exceptions that should trigger retries
        on_retry: Optional callback function called on each retry (attempt_num, exception)
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    # Check if this is a non-retryable error
                    if isinstance(e, NonRetryableError):
                        raise
                    
                    # Don't retry on last attempt
                    if attempt == max_retries:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    time.sleep(delay)
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


def is_retryable_aws_error(error: ClientError) -> bool:
    """
    Check if an AWS error is retryable.
    
    Args:
        error: Boto3 ClientError
        
    Returns:
        True if error is retryable, False otherwise
    """
    error_code = error.response.get('Error', {}).get('Code', '')
    
    # Retryable error codes
    retryable_codes = {
        'ThrottlingException',
        'Throttling',
        'ServiceUnavailable',
        'InternalServerError',
        'TooManyRequestsException',
        'RequestTimeout',
        'RequestTimeoutException',
        'SlowDown',
        'ProvisionedThroughputExceededException'
    }
    
    # Non-retryable error codes
    non_retryable_codes = {
        'InvalidParameterException',
        'InvalidRequestException',
        'AccessDeniedException',
        'ResourceNotFoundException',
        'ValidationException',
        'UnsupportedDocumentException',
        'BadDocumentException',
        'DocumentTooLargeException',
        'InvalidS3ObjectException'
    }
    
    if error_code in retryable_codes:
        return True
    
    if error_code in non_retryable_codes:
        return False
    
    # Default: retry on 5xx errors, don't retry on 4xx errors
    status_code = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
    return 500 <= status_code < 600


def retry_aws_operation(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> T:
    """
    Retry an AWS operation with intelligent error handling.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        on_retry: Optional callback for retry events
        
    Returns:
        Result of the function
        
    Raises:
        NonRetryableError: If error is not retryable
        Exception: If all retries are exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except ClientError as e:
            last_exception = e
            
            # Check if error is retryable
            if not is_retryable_aws_error(e):
                raise NonRetryableError(f"Non-retryable AWS error: {e}") from e
            
            # Don't retry on last attempt
            if attempt == max_retries:
                break
            
            # Calculate delay
            delay = min(
                initial_delay * (2.0 ** attempt),
                max_delay
            )
            
            # Add jitter
            delay = delay * (0.5 + random.random() * 0.5)
            
            # Call retry callback
            if on_retry:
                on_retry(attempt + 1, e)
            
            time.sleep(delay)
        except Exception as e:
            # Non-AWS exceptions: don't retry
            raise NonRetryableError(f"Non-retryable error: {e}") from e
    
    # All retries exhausted
    raise Exception(f"Operation failed after {max_retries + 1} attempts: {last_exception}") from last_exception
