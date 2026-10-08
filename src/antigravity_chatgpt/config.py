"""
Configuration management for Antigravity ChatGPT bridge.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Bridge runtime settings."""

    host: str = Field(default="0.0.0.0", description="Bridge listening host")
    port: int = Field(default=8000, description="Bridge listening port")
    base_sandbox_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("ANTIGRAVITY_SANDBOX_DIR", "/tmp/antigravity-sandboxes")),
        description="Root directory for ephemeral task sandboxes"
    )
    agy_binary_path: str = Field(
        default=os.getenv("AGY_BINARY_PATH", "agy"),
        description="Path or binary name for Antigravity CLI"
    )
    default_model: str = Field(
        default="gemini-3.8-flash-high",
        description="Default Gemini model tier"
    )
    default_effort: str = Field(
        default="high",
        description="Default reasoning effort (low, medium, high, xhigh)"
    )
    sync_timeout_seconds: int = Field(
        default=30,
        description="Maximum seconds to hold HTTP connection before delegating to background async polling"
    )
    task_retention_minutes: int = Field(
        default=60,
        description="Duration to retain async task results in memory"
    )


settings = Settings()
