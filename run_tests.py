"""
Test runner script for invoice processing tests.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py unit               # Run only unit tests
    python run_tests.py integration        # Run only integration tests
    python run_tests.py validation         # Run only validation tests
    python run_tests.py batch              # Run batch tests with multiple invoices
"""
import sys
import subprocess
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def run_tests(test_type="all"):
    """Run tests based on type."""
    test_map = {
        "all": ["tests/"],
        "unit": ["tests/test_canonical_builder.py"],
        "integration": ["tests/test_pipeline_integration.py"],
        "validation": ["tests/test_validation.py"],
        "batch": ["tests/test_multiple_invoices.py"],
    }
    
    test_paths = test_map.get(test_type, test_map["all"])
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"] + test_paths + ["-v", "--tb=short"]
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main entry point."""
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_type not in ["all", "unit", "integration", "validation", "batch"]:
        print(f"❌ Unknown test type: {test_type}")
        print("Available types: all, unit, integration, validation, batch")
        return 1
    
    return run_tests(test_type)


if __name__ == "__main__":
    sys.exit(main())
