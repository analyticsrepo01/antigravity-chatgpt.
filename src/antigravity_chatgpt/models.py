"""
Pydantic request and response schemas for ChatGPT Antigravity bridge.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Request payload to trigger an Antigravity agent execution turn."""

    prompt: str = Field(
        ...,
        description="The software engineering or coding task instruction for Antigravity."
    )
    model: str = Field(
        default="gemini-3.8-flash-high",
        description="Gemini model tier."
    )
    effort: str = Field(
        default="high",
        description="Reasoning effort level (low, medium, high, xhigh, max)."
    )
    git_repo_url: Optional[str] = Field(
        default=None,
        description="Optional Git repository URL to clone and operate on."
    )
    git_branch: Optional[str] = Field(
        default=None,
        description="Optional Git branch or tag."
    )
    wait_seconds: int = Field(
        default=30,
        ge=5,
        le=35,
        description="Max seconds to wait before falling back to async polling."
    )


class FileDiff(BaseModel):
    """File change diff metadata."""

    path: str
    status: str = Field(description="modified, created, or deleted")
    diff: Optional[str] = None


class CommandRecord(BaseModel):
    """Terminal command executed during the agent turn."""

    command: str
    exit_code: int
    output_snippet: Optional[str] = None


class AgentRunResponse(BaseModel):
    """Synchronous result of an Antigravity agent run."""

    status: str = Field(default="completed", description="completed or failed")
    summary: str = Field(description="Summary of work completed by Antigravity")
    files_changed: List[FileDiff] = Field(default_factory=list)
    commands_executed: List[CommandRecord] = Field(default_factory=list)
    execution_time_seconds: float = Field(default=0.0)


class AsyncTaskAcceptedResponse(BaseModel):
    """Returned when a task takes longer than wait_seconds."""

    task_id: str
    status: str = "running"
    poll_url: str
    message: str = "Agent task is executing asynchronously. Please poll the poll_url for completion."


class TaskStatusResponse(BaseModel):
    """Async task status polled by ChatGPT."""

    task_id: str
    status: str = Field(description="queued, running, completed, failed")
    result: Optional[AgentRunResponse] = None
    error: Optional[str] = None


class VerifyResponse(BaseModel):
    """Gemini API Key verification response."""

    valid: bool
    message: str


class ModelDescriptor(BaseModel):
    """Gemini model metadata."""

    id: str
    name: str
    recommended_for: str


class ModelsResponse(BaseModel):
    """List of available models."""

    models: List[ModelDescriptor]


class ErrorResponse(BaseModel):
    """Standardized error response."""

    code: str
    message: str
