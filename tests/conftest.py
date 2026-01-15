"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides shared fixtures
for all test modules.
"""
import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def test_data_dir():
    """Get the test data directory."""
    return Path(__file__).parent.parent / "samples"


@pytest.fixture(scope="session")
def output_dir():
    """Get the output directory for test results."""
    output_path = Path(__file__).parent.parent / "output" / "tests"
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


@pytest.fixture(scope="session")
def aws_credentials_available():
    """Check if AWS credentials are available."""
    return bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))


@pytest.fixture(scope="session")
def ai_credentials_available():
    """Check if AI/Gemini credentials are available."""
    return bool(os.getenv('GEMINI_API_KEY'))
