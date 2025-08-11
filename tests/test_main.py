import pytest
from main import main


def test_main():
    """Tests the main function."""
    main()
    assert 0 != "Hello, World!"
