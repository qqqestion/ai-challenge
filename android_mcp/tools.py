"""
Android device control tools for MCP.

Provides commands to open a deeplink, launch an app, and kill an app via ADB.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any, Dict, Optional

logger = logging.getLogger("android-mcp-server.tools")


class AdbError(RuntimeError):
    """Raised when an ADB command fails."""


def _ensure_adb_available() -> str:
    """Return adb path or raise if not available."""
    adb_path = shutil.which("adb")
    if not adb_path:
        raise AdbError("adb is not available in PATH")
    return adb_path


async def _run_adb_command(args: list[str], timeout: float = 15.0) -> Dict[str, Any]:
    """Run adb command and capture output."""
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout)
    except asyncio.TimeoutError:
        process.kill()
        raise AdbError(f"Command timed out: {' '.join(args)}")

    stdout = stdout_bytes.decode("utf-8", errors="ignore").strip()
    stderr = stderr_bytes.decode("utf-8", errors="ignore").strip()

    if process.returncode != 0:
        raise AdbError(f"ADB error (code {process.returncode}): {stderr or stdout}")

    return {
        "success": True,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": process.returncode,
    }


async def open_deeplink(deeplink: str, package_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Open a deeplink on the connected Android device.

    Args:
        deeplink: Full URI to open.
        package_name: Optional package to target.
    """
    if not deeplink or not deeplink.strip():
        raise ValueError("deeplink must not be empty")

    adb_path = _ensure_adb_available()
    cmd = [
        adb_path,
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        deeplink.strip(),
    ]

    if package_name:
        cmd.extend(["-p", package_name.strip()])

    logger.info("Opening deeplink: %s", deeplink)
    result = await _run_adb_command(cmd)
    result["message"] = "Deeplink opened"
    return result


async def open_app(
    package_name: str,
    activity: Optional[str] = None,
    use_monkey: bool = False,
) -> Dict[str, Any]:
    """
    Launch an Android application.

    Args:
        package_name: Application package name.
        activity: Optional activity name (e.g., .MainActivity or pkg/.Activity).
        use_monkey: If True and activity is not provided, use monkey launcher.
    """
    if not package_name or not package_name.strip():
        raise ValueError("package_name must not be empty")

    adb_path = _ensure_adb_available()
    package_name = package_name.strip()

    if activity:
        component = activity.strip()
        if "/" not in component:
            component = f"{package_name}/{component}"
        cmd = [adb_path, "shell", "am", "start", "-n", component]
        action = f"Starting activity {component}"
    elif use_monkey:
        cmd = [
            adb_path,
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
        action = f"Launching app {package_name} via monkey"
    else:
        # Fallback: try MAIN/LAUNCHER without explicit activity
        cmd = [
            adb_path,
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            "-p",
            package_name,
        ]
        action = f"Launching app {package_name} via MAIN/LAUNCHER"

    logger.info(action)
    result = await _run_adb_command(cmd)
    result["message"] = "Application started"
    return result


async def kill_app(package_name: str) -> Dict[str, Any]:
    """
    Kill (force-stop) an Android application.

    Args:
        package_name: Application package name.
    """
    if not package_name or not package_name.strip():
        raise ValueError("package_name must not be empty")

    adb_path = _ensure_adb_available()
    cmd = [adb_path, "shell", "am", "force-stop", package_name.strip()]

    logger.info("Killing app: %s", package_name)
    result = await _run_adb_command(cmd)
    result["message"] = "Application killed"
    return result


