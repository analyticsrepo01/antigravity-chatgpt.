"""
FastAPI application exposing OpenAPI endpoints for ChatGPT Custom Action integration.
"""

import asyncio
import uuid
from typing import Dict, Optional
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from antigravity_chatgpt.config import settings
from antigravity_chatgpt.executor import AntigravityExecutor
from antigravity_chatgpt.models import (
    AgentRunRequest,
    AgentRunResponse,
    AsyncTaskAcceptedResponse,
    ErrorResponse,
    ModelDescriptor,
    ModelsResponse,
    TaskStatusResponse,
    VerifyResponse,
)
from antigravity_chatgpt.security import extract_gemini_key, verify_gemini_key
from antigravity_chatgpt.workspace import Workspace

app = FastAPI(
    title="Antigravity Agent Bridge for ChatGPT",
    description="Bridge Google Antigravity autonomous coding agent with OpenAI ChatGPT using BYOK Gemini API key.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = AntigravityExecutor()

# In-memory store for async background tasks
tasks_store: Dict[str, TaskStatusResponse] = {}


@app.get("/health")
def health_check():
    """Service health check."""
    return {"status": "ok", "service": "antigravity-chatgpt-bridge"}


@app.get("/v1/auth/verify", response_model=VerifyResponse, responses={401: {"model": ErrorResponse}})
async def verify_key(api_key: str = Depends(extract_gemini_key)):
    """Verifies that the provided Gemini API key is valid."""
    is_valid = await verify_gemini_key(api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "The provided Gemini API key failed validation with Google AI Studio."}
        )
    return VerifyResponse(
        valid=True,
        message="Gemini API key is valid and connected to Google AI Studio."
    )


@app.get("/v1/models", response_model=ModelsResponse)
def list_models():
    """Lists available Gemini models supported by Antigravity."""
    return ModelsResponse(
        models=[
            ModelDescriptor(
                id="gemini-3.8-flash-high",
                name="Gemini 3.8 Flash (High Reasoning)",
                recommended_for="Default: Complex coding, multi-file refactoring, SWE-bench debugging"
            ),
            ModelDescriptor(
                id="gemini-3.8-flash-medium",
                name="Gemini 3.8 Flash (Medium Reasoning)",
                recommended_for="Feature implementations, unit test suites"
            ),
            ModelDescriptor(
                id="gemini-3.8-flash-low",
                name="Gemini 3.8 Flash (Low Reasoning)",
                recommended_for="Quick fixes, syntax correction, documentation"
            ),
            ModelDescriptor(
                id="gemini-3.7-flash-high",
                name="Gemini 3.7 Flash (High Reasoning)",
                recommended_for="Alternative high-speed coding model"
            ),
            ModelDescriptor(
                id="gemini-3.1-pro-high",
                name="Gemini 3.1 Pro (High Reasoning)",
                recommended_for="Large architectural design & multi-agent planning"
            ),
        ]
    )


async def _run_agent_task_background(
    task_id: str,
    request: AgentRunRequest,
    api_key: str,
    workspace: Workspace
):
    """Executes the task in background and records state in tasks_store."""
    tasks_store[task_id].status = "running"
    try:
        await workspace.setup(
            git_repo_url=request.git_repo_url,
            git_branch=request.git_branch
        )
        res = await executor.execute(
            prompt=request.prompt,
            gemini_api_key=api_key,
            workspace=workspace,
            model=request.model,
            effort=request.effort,
        )
        tasks_store[task_id].status = "completed"
        tasks_store[task_id].result = res
    except Exception as exc:
        tasks_store[task_id].status = "failed"
        tasks_store[task_id].error = str(exc)


@app.post(
    "/v1/agent/run",
    response_model=AgentRunResponse,
    responses={
        202: {"model": AsyncTaskAcceptedResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    }
)
async def run_agent_task(
    request: AgentRunRequest,
    response: Response,
    api_key: str = Depends(extract_gemini_key)
):
    """
    Executes an Antigravity agent turn.
    Returns 200 with result if finished within wait_seconds;
    otherwise returns 202 Accepted with task_id to avoid ChatGPT 45s timeout.
    """
    task_id = f"task_{uuid.uuid4().hex[:10]}"
    workspace = Workspace()

    tasks_store[task_id] = TaskStatusResponse(
        task_id=task_id,
        status="queued"
    )

    bg_task = asyncio.create_task(
        _run_agent_task_background(task_id, request, api_key, workspace)
    )

    try:
        # Wait up to request.wait_seconds (default 30s)
        await asyncio.wait_for(asyncio.shield(bg_task), timeout=request.wait_seconds)
    except asyncio.TimeoutError:
        # Task is still running, return 202 Accepted so ChatGPT does not timeout!
        response.status_code = status.HTTP_202_ACCEPTED
        return AsyncTaskAcceptedResponse(
            task_id=task_id,
            status="running",
            poll_url=f"/v1/tasks/{task_id}",
            message=f"Agent execution is underway. Poll /v1/tasks/{task_id} for completion."
        )

    task_record = tasks_store.get(task_id)
    if task_record and task_record.status == "completed" and task_record.result:
        return task_record.result
    elif task_record and task_record.status == "failed":
        err_msg = task_record.error or "Unknown agent execution failure"
        if "GEMINI_QUOTA_EXHAUSTED" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "GEMINI_QUOTA_EXHAUSTED", "message": err_msg}
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EXECUTION_ERROR", "message": err_msg}
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "UNEXPECTED_STATE", "message": "Task completed without result."}
    )


@app.get(
    "/v1/tasks/{task_id}",
    response_model=TaskStatusResponse,
    responses={404: {"model": ErrorResponse}}
)
def get_task_status(task_id: str):
    """Retrieves current status of an async agent task."""
    record = tasks_store.get(task_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}
        )
    return record


def main():
    """CLI launcher for bridge server."""
    uvicorn.run(
        "antigravity_chatgpt.app:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )


if __name__ == "__main__":
    main()
