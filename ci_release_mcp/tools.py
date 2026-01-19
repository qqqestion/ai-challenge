"""
CI Release MCP tools for local release automation.

All operations are executed against a hardcoded repository path:
    ~/Programming/ai-challenge-server
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_PATH = Path("~/Programming/ai-challenge-server").expanduser().resolve()
START_SERVER_SCRIPT = Path(
    "/Users/vchslv-mrzv/Programming/ai-challenge-server/deploy.sh"
).resolve()

_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]*$")


def _ensure_repo_exists() -> None:
    if not REPO_PATH.exists():
        raise FileNotFoundError(f"Repository path does not exist: {REPO_PATH}")


def _ensure_git_available() -> None:
    if not shutil.which("git"):
        raise RuntimeError("git binary not found in PATH")


def _run_git(args: List[str]) -> str:
    result = subprocess.run(
        args,
        cwd=REPO_PATH,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _branch_name(version: str) -> str:
    v = (version or "").strip()
    if not v:
        raise ValueError("version must not be empty")
    if not _VERSION_RE.match(v):
        raise ValueError(
            "version contains unsupported characters; allowed: alnum, '.', '_', '-'"
        )
    return f"release/{v}"


def _find_activation_script(repo_path: Path) -> Optional[Path]:
    candidates = [
        repo_path / ".venv" / "bin" / "activate",
        repo_path / "venv" / "bin" / "activate",
        repo_path / "env" / "bin" / "activate",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _truncate(text: str, limit: int = 20000) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    head = text[:limit]
    return head + "\n\n... [truncated] ..."


def _run_bash_in_repo(script: str, timeout_s: int) -> Dict[str, Any]:
    completed = subprocess.run(
        ["/bin/bash", "-lc", script],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    stdout = _truncate(completed.stdout or "")
    stderr = _truncate(completed.stderr or "")
    return {
        "exit_code": int(completed.returncode),
        "stdout": stdout,
        "stderr": stderr,
        "output": _truncate((stdout + "\n" + stderr).strip()),
    }


async def create_release_branch(version: str) -> Dict[str, Any]:
    """Create (or reset) release/<version> branch from current HEAD."""
    try:
        _ensure_repo_exists()
        _ensure_git_available()
        branch = _branch_name(version)

        # Verify repository
        await asyncio.to_thread(
            _run_git, ["git", "rev-parse", "--is-inside-work-tree"]
        )

        # Create/reset and checkout the release branch from current HEAD
        await asyncio.to_thread(_run_git, ["git", "checkout", "-B", branch])

        return {"success": True, "branch": branch}
    except subprocess.TimeoutExpired as exc:
        return {"success": False, "branch": _branch_name(version), "error": str(exc)}
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip() or str(exc)
        return {"success": False, "branch": _branch_name(version), "error": err}
    except Exception as exc:
        return {"success": False, "branch": _branch_name(version), "error": str(exc)}


async def run_tests_on_release_branch(version: str) -> Dict[str, Any]:
    """Checkout release/<version> and run `python manage.py test` with repo environment."""
    branch = _branch_name(version)
    try:
        _ensure_repo_exists()
        _ensure_git_available()

        await asyncio.to_thread(_run_git, ["git", "checkout", branch])

        activate = _find_activation_script(REPO_PATH)
        if activate:
            cmd = f'source "{activate}" && python manage.py test'
        else:
            cmd = "python manage.py test"

        script = "set -euo pipefail\n" + cmd + "\n"
        res = await asyncio.to_thread(_run_bash_in_repo, script, 3600)

        status = "passed" if res["exit_code"] == 0 else "failed"
        success = res["exit_code"] == 0
        return {
            "success": success,
            "branch": branch,
            "status": status,
            "exit_code": res["exit_code"],
            "output": res["output"],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "branch": branch,
            "status": "error",
            "exit_code": -1,
            "output": f"Timeout: {exc}",
        }
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip() or str(exc)
        return {
            "success": False,
            "branch": branch,
            "status": "error",
            "exit_code": int(getattr(exc, "returncode", 1) or 1),
            "output": err,
        }
    except Exception as exc:
        return {
            "success": False,
            "branch": branch,
            "status": "error",
            "exit_code": 1,
            "output": str(exc),
        }


async def start_server_on_release_branch(version: str) -> Dict[str, Any]:
    """Checkout release/<version> and run the hardcoded server start script (stub)."""
    branch = _branch_name(version)
    try:
        _ensure_repo_exists()
        _ensure_git_available()

        await asyncio.to_thread(_run_git, ["git", "checkout", branch])

        if not START_SERVER_SCRIPT.is_file():
            raise FileNotFoundError(f"Start script not found: {START_SERVER_SCRIPT}")

        completed = await asyncio.to_thread(
            subprocess.run,
            ["/bin/zsh", str(START_SERVER_SCRIPT)],
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
        )

        stdout = _truncate(completed.stdout or "")
        stderr = _truncate(completed.stderr or "")
        success = int(completed.returncode) == 0
        return {
            "success": success,
            "branch": branch,
            "exit_code": int(completed.returncode),
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip() or str(exc)
        return {
            "success": False,
            "branch": branch,
            "exit_code": int(getattr(exc, "returncode", 1) or 1),
            "stdout": "",
            "stderr": err,
        }
    except Exception as exc:
        return {
            "success": False,
            "branch": branch,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
        }


def to_json(data: Dict[str, Any]) -> str:
    """Serialize result to JSON string."""
    return json.dumps(data, ensure_ascii=False, indent=2)


