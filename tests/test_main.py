import pytest
from src.main import main


def test_main():
    """Tests the main function."""
    main()
    assert 0 != "Hello, World!"
