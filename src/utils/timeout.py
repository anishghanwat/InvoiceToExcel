"""
Timeout utilities for long-running operations.
"""
import signal
import time
from typing import Callable, TypeVar, Optional
from contextlib import contextmanager

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


@contextmanager
def timeout_context(seconds: float):
    """
    Context manager for timeout handling.
    
    Args:
        seconds: Timeout in seconds
        
    Raises:
        TimeoutError: If operation exceeds timeout
        
    Example:
        with timeout_context(30.0):
            long_running_operation()
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up signal handler (Unix only)
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows doesn't support SIGALRM, use polling instead
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            if elapsed > seconds:
                raise TimeoutError(f"Operation timed out after {seconds} seconds")


def with_timeout(func: Callable[..., T], timeout_seconds: float, *args, **kwargs) -> T:
    """
    Execute a function with timeout.
    
    Args:
        func: Function to execute
        timeout_seconds: Timeout in seconds
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function
        
    Returns:
        Function result
        
    Raises:
        TimeoutError: If function exceeds timeout
    """
    if hasattr(signal, 'SIGALRM'):
        # Unix: Use signal-based timeout
        with timeout_context(timeout_seconds):
            return func(*args, **kwargs)
    else:
        # Windows: Use polling (less precise)
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
        return result


class TimeoutGuard:
    """
    Timeout guard for operations that need to check elapsed time periodically.
    Useful for operations that can't be interrupted with signals.
    """
    
    def __init__(self, timeout_seconds: float):
        """
        Initialize timeout guard.
        
        Args:
            timeout_seconds: Maximum time allowed in seconds
        """
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()
    
    def check(self) -> None:
        """
        Check if timeout has been exceeded.
        
        Raises:
            TimeoutError: If timeout exceeded
        """
        elapsed = time.time() - self.start_time
        if elapsed > self.timeout_seconds:
            raise TimeoutError(f"Operation timed out after {self.timeout_seconds} seconds")
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    def remaining(self) -> float:
        """Get remaining time in seconds."""
        return max(0, self.timeout_seconds - self.elapsed())
