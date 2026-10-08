"""
Security and authentication utilities for Antigravity ChatGPT bridge.
"""

import re
from pathlib import Path
from typing import Optional
from fastapi import Header, HTTPException, status
import httpx

API_KEY_REGEX = re.compile(r"AIza[0-9A-Za-z-_]{30,45}")


def sanitize_text(text: str) -> str:
    """Redacts any exposed Gemini API keys from logs and response text."""
    if not text:
        return text
    return API_KEY_REGEX.sub("[REDACTED_API_KEY]", text)


def extract_gemini_key(
    authorization: Optional[str] = Header(None),
    x_gemini_api_key: Optional[str] = Header(None)
) -> str:
    """Extracts Gemini API Key from Bearer Authorization or X-Gemini-API-Key header."""
    if x_gemini_api_key and x_gemini_api_key.strip():
        return x_gemini_api_key.strip()

    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        if len(parts) == 1:
            return parts[0].strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "MISSING_API_KEY",
            "message": "Missing Gemini API key. Provide Bearer token or X-Gemini-API-Key header."
        }
    )


async def verify_gemini_key(api_key: str) -> bool:
    """Verifies that the Gemini API key is valid against Google AI Studio."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            return resp.status_code == 200
        except Exception:
            return False


def validate_safe_path(base_dir: Path, target_path: Path) -> Path:
    """Ensures target_path resolves strictly within base_dir to prevent path traversal."""
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()
    if not str(resolved_target).startswith(str(resolved_base)):
        raise ValueError(f"Path traversal detected: {target_path} is outside {base_dir}")
    return resolved_target
