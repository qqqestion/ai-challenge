"""
Git MCP tools for local Git operations.

Provides utilities to inspect the current branch and list local branches
for a given repository path.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_REPO_PATH = Path("/Users/vchslv-mrzv/Programming/ai-challenge")


def _ensure_git_available() -> None:
    """Ensure git binary is available in PATH."""
    if not shutil.which("git"):
        raise RuntimeError("git binary not found in PATH")


def _resolve_repo_path(repo_path: str | None) -> Path:
    """Resolve repository path, defaulting to the project root."""
    path = Path(repo_path).expanduser() if repo_path else DEFAULT_REPO_PATH
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {path}")
    return path


def _run_git_command(repo_path: Path, args: List[str]) -> str:
    """Run a git command in the given repository and return stdout."""
    result = subprocess.run(
        args,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


async def get_current_branch(repo_path: str | None = None) -> Dict[str, Any]:
    """Return the current branch for the repository."""
    try:
        _ensure_git_available()
        repo_dir = _resolve_repo_path(repo_path)

        # Verify repository
        await asyncio.to_thread(
            _run_git_command, repo_dir, ["git", "rev-parse", "--is-inside-work-tree"]
        )

        branch = await asyncio.to_thread(
            _run_git_command, repo_dir, ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        )

        return {
            "success": True,
            "repo_path": str(repo_dir),
            "branch": branch,
        }
    except subprocess.CalledProcessError as exc:
        return {
            "success": False,
            "repo_path": str(repo_path or DEFAULT_REPO_PATH),
            "error": exc.stderr.strip() if exc.stderr else str(exc),
        }
    except Exception as exc:
        return {
            "success": False,
            "repo_path": str(repo_path or DEFAULT_REPO_PATH),
            "error": str(exc),
        }


async def list_branches(repo_path: str | None = None) -> Dict[str, Any]:
    """List local branches for the repository."""
    try:
        _ensure_git_available()
        repo_dir = _resolve_repo_path(repo_path)

        # Verify repository
        await asyncio.to_thread(
            _run_git_command, repo_dir, ["git", "rev-parse", "--is-inside-work-tree"]
        )

        branches_raw = await asyncio.to_thread(
            _run_git_command,
            repo_dir,
            ["git", "branch", "--format", "%(refname:short)"],
        )
        branches = [b.strip() for b in branches_raw.splitlines() if b.strip()]

        return {
            "success": True,
            "repo_path": str(repo_dir),
            "branches": branches,
            "count": len(branches),
        }
    except subprocess.CalledProcessError as exc:
        return {
            "success": False,
            "repo_path": str(repo_path or DEFAULT_REPO_PATH),
            "error": exc.stderr.strip() if exc.stderr else str(exc),
        }
    except Exception as exc:
        return {
            "success": False,
            "repo_path": str(repo_path or DEFAULT_REPO_PATH),
            "error": str(exc),
        }


def to_json(data: Dict[str, Any]) -> str:
    """Serialize result to JSON string."""
    return json.dumps(data, ensure_ascii=False, indent=2)

