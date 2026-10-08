"""
Antigravity agent process executor with BYOK Gemini API key injection.
"""

import asyncio
import json
import os
import shutil
import time
from typing import List, Tuple
from antigravity_chatgpt.config import settings
from antigravity_chatgpt.models import AgentRunResponse, CommandRecord, FileDiff
from antigravity_chatgpt.security import sanitize_text
from antigravity_chatgpt.workspace import Workspace


class AntigravityExecutor:
    """Executes Antigravity agent sessions within sandboxed workspaces."""

    def __init__(self, binary_path: str = settings.agy_binary_path):
        resolved = shutil.which(binary_path)
        self.binary_path = resolved if resolved else binary_path

    async def execute(
        self,
        prompt: str,
        gemini_api_key: str,
        workspace: Workspace,
        model: str = settings.default_model,
        effort: str = settings.default_effort,
    ) -> AgentRunResponse:
        """Executes an Antigravity agent turn using the user's Gemini API key."""
        start_time = time.time()

        # Build isolated child process environment
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = gemini_api_key
        env["modelProvider"] = "gemini"

        cmd = [
            self.binary_path,
            "--print", prompt,
            "--model", model,
            "--effort", effort,
            "--output-format", "json",
            "--dangerously-skip-permissions",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace.path),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout_bytes, stderr_bytes = await proc.communicate()
        raw_stdout = stdout_bytes.decode(errors="replace")
        raw_stderr = stderr_bytes.decode(errors="replace")

        elapsed = round(time.time() - start_time, 2)

        # Sanitize logs of any leaked keys
        clean_stdout = sanitize_text(raw_stdout)
        clean_stderr = sanitize_text(raw_stderr)

        if proc.returncode != 0:
            if "RESOURCE_EXHAUSTED" in clean_stderr or "429" in clean_stderr:
                raise RuntimeError("GEMINI_QUOTA_EXHAUSTED: Gemini API rate limit or quota exceeded.")
            raise RuntimeError(f"Antigravity execution failed (exit {proc.returncode}): {clean_stderr or clean_stdout}")

        # Try parsing JSON output from agy
        summary = clean_stdout.strip()
        files_changed: List[FileDiff] = []
        commands_executed: List[CommandRecord] = []

        try:
            parsed = json.loads(clean_stdout)
            if isinstance(parsed, dict):
                summary = parsed.get("summary") or parsed.get("response") or parsed.get("output") or clean_stdout
                # Extract commands if present
                if "commands" in parsed and isinstance(parsed["commands"], list):
                    for c in parsed["commands"]:
                        commands_executed.append(
                            CommandRecord(
                                command=c.get("command", ""),
                                exit_code=c.get("exit_code", 0),
                                output_snippet=c.get("output")
                            )
                        )
        except Exception:
            # Fallback to plain text stdout
            pass

        # Inspect workspace for git diffs
        git_diffs = await workspace.get_git_diffs()
        if git_diffs:
            files_changed.extend(git_diffs)

        return AgentRunResponse(
            status="completed",
            summary=summary,
            files_changed=files_changed,
            commands_executed=commands_executed,
            execution_time_seconds=elapsed
        )
