"""
Report MCP tools.

Provides a tool to create report files in the project `reports/` directory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict


def _normalize_report_name(raw_name: str) -> str:
    """Normalize report name to a safe filesystem-friendly string."""
    name = raw_name.strip()
    if not name:
        raise ValueError("report_name must not be empty")

    name = name.lower()
    # Replace invalid chars with underscore
    name = re.sub(r"[^a-z0-9._-]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    if not name:
        raise ValueError("report_name became empty after normalization")

    # Ensure .md extension
    if not name.endswith(".md"):
        name = f"{name}.md"
    return name


async def create_report(report_name: str, title: str, content: str) -> Dict[str, Any]:
    """
    Create a report file with the given name, title, and content.

    The file will be stored under the project `reports/` directory.
    File format: first line is the title, then an empty line, then content.
    """
    if not title.strip():
        raise ValueError("title must not be empty")

    if content is None:
        raise ValueError("content must not be None")

    normalized_name = _normalize_report_name(report_name)

    base_dir = Path(__file__).resolve().parent.parent
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    target_path = reports_dir / normalized_name

    file_text = f"# {title}\n\n{content}\n"
    target_path.write_text(file_text, encoding="utf-8")

    return {
        "success": True,
        "path": str(target_path),
        "filename": normalized_name,
        "message": "Report created",
    }


