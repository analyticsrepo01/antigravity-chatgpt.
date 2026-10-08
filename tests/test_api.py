"""
Tests for Antigravity ChatGPT bridge API endpoints.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from antigravity_chatgpt.app import app

client = TestClient(app)


def test_health():
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_models():
    """Verify models catalog endpoint."""
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    model_ids = [m["id"] for m in data["models"]]
    assert "gemini-3.8-flash-high" in model_ids
    assert "gemini-3.1-pro-high" in model_ids


def test_verify_missing_key():
    """Verify endpoint rejects requests missing API key header."""
    response = client.get("/v1/auth/verify")
    assert response.status_code == 401


@patch("antigravity_chatgpt.app.verify_gemini_key", new_callable=AsyncMock)
def test_verify_valid_key(mock_verify):
    """Verify endpoint accepts valid key."""
    mock_verify.return_value = True
    response = client.get(
        "/v1/auth/verify",
        headers={"Authorization": "Bearer AIzaSyFakeValidKey1234567890abcdef"}
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


@patch("antigravity_chatgpt.app.verify_gemini_key", new_callable=AsyncMock)
def test_verify_invalid_key(mock_verify):
    """Verify endpoint rejects invalid key."""
    mock_verify.return_value = False
    response = client.get(
        "/v1/auth/verify",
        headers={"X-Gemini-API-Key": "AIzaSyInvalidKey"}
    )
    assert response.status_code == 401
