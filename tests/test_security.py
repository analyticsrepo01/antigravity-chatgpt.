"""
Tests for security sanitization and path traversal safeguards.
"""

from pathlib import Path
import pytest
from antigravity_chatgpt.security import sanitize_text, validate_safe_path


def test_sanitize_text():
    raw = "Error calling endpoint with key AIzaSyD3x4mpleK3y1234567890abcdef1234 failed"
    sanitized = sanitize_text(raw)
    assert "AIzaSyD3x4mpleK3y1234567890abcdef1234" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_validate_safe_path():
    base = Path("/tmp/sandboxes/ws_123")
    safe_child = base / "src" / "main.py"
    # Valid child
    validated = validate_safe_path(base, safe_child)
    assert str(validated).startswith(str(base.resolve()))

    # Traversal attack
    traversal = base / ".." / ".." / "etc" / "passwd"
    with pytest.raises(ValueError, match="Path traversal detected"):
        validate_safe_path(base, traversal)
