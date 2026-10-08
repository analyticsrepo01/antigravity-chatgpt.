"""
Workspace and sandboxing management for Antigravity tasks.
"""

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from antigravity_chatgpt.config import settings
from antigravity_chatgpt.models import FileDiff
from antigravity_chatgpt.security import validate_safe_path


class Workspace:
    """Encapsulates an isolated filesystem workspace for an agent turn."""

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id or f"ws_{uuid.uuid4().hex[:10]}"
        self.path: Path = settings.base_sandbox_dir / self.workspace_id

    async def setup(self, git_repo_url: Optional[str] = None, git_branch: Optional[str] = None) -> None:
        """Initializes the workspace directory and clones git repo if requested."""
        settings.base_sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.path.mkdir(parents=True, exist_ok=True)

        if git_repo_url:
            clone_cmd = ["git", "clone", "--depth", "1"]
            if git_branch:
                clone_cmd.extend(["--branch", git_branch])
            clone_cmd.extend([git_repo_url, str(self.path)])

            proc = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"Git clone failed: {stderr.decode(errors='ignore')}")

    async def get_git_diffs(self) -> List[FileDiff]:
        """Collects git diffs from the workspace if it is a git repository."""
        git_dir = self.path / ".git"
        if not git_dir.exists():
            return []

        # Run git status --porcelain
        status_proc = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=str(self.path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        status_out, _ = await status_proc.communicate()
        status_lines = status_out.decode().splitlines()

        diffs: List[FileDiff] = []
        for line in status_lines:
            if len(line) < 3:
                continue
            code = line[:2].strip()
            file_path = line[3:].strip()
            file_status = "modified"
            if "A" in code or "?" in code:
                file_status = "created"
            elif "D" in code:
                file_status = "deleted"

            # Get diff content
            diff_proc = await asyncio.create_subprocess_exec(
                "git", "diff", "HEAD", "--", file_path,
                cwd=str(self.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            diff_out, _ = await diff_proc.communicate()
            diff_str = diff_out.decode(errors="ignore")

            diffs.append(
                FileDiff(
                    path=file_path,
                    status=file_status,
                    diff=diff_str if diff_str else None
                )
            )

        return diffs

    def cleanup(self) -> None:
        """Deletes the sandbox workspace and contents."""
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)
