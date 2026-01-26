"""
Analytics MCP tools.

Provides grep-like search over a fixed local analytics digest JSON file.
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Iterable, Tuple


DEFAULT_DIGEST_FILENAME = "analytics-digest-1777822926768606593.json"


def _resolve_digest_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    digest_path = base_dir / "resources" / DEFAULT_DIGEST_FILENAME
    if not digest_path.exists():
        raise FileNotFoundError(f"Analytics digest not found: {digest_path}")
    return digest_path


def _compile_matcher(pattern: str, *, ignore_case: bool, regex: bool) -> Callable[[str], bool]:
    if not pattern:
        raise ValueError("pattern must not be empty")

    if regex:
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags=flags)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern: {exc}") from exc

        return lambda line: compiled.search(line) is not None

    if ignore_case:
        needle = pattern.casefold()
        return lambda line: needle in line.casefold()

    return lambda line: pattern in line


def _format_grep_line(file_path: Path, *, line: str, line_no: int, with_line_numbers: bool) -> str:
    text = line.rstrip("\n")
    if with_line_numbers:
        return f"{file_path}:{line_no}:{text}"
    return f"{file_path}:{text}"


def _grep_lines(
    lines: Iterable[str],
    *,
    file_path: Path,
    matcher: Callable[[str], bool],
    with_line_numbers: bool,
    max_matches: int,
    before_context: int,
    after_context: int,
) -> tuple[str, int, bool]:
    if max_matches < 1:
        raise ValueError("max_matches must be >= 1")
    if before_context < 0 or after_context < 0:
        raise ValueError("before_context and after_context must be >= 0")

    output: list[str] = []
    before: Deque[Tuple[int, str]] = deque(maxlen=before_context)
    after_remaining = 0
    matches = 0
    truncated = False
    last_emitted_line_no = 0
    stop_after_context = False

    def emit(lineno: int, text_line: str) -> None:
        nonlocal last_emitted_line_no
        if lineno <= last_emitted_line_no:
            return
        output.append(
            _format_grep_line(
                file_path, line=text_line, line_no=lineno, with_line_numbers=with_line_numbers
            )
        )
        last_emitted_line_no = lineno

    for lineno, line in enumerate(lines, start=1):
        is_match = matcher(line)

        if is_match:
            matches += 1

            # Emit before-context for this match.
            for prev_lineno, prev_line in before:
                emit(prev_lineno, prev_line)

            emit(lineno, line)

            after_remaining = max(after_remaining, after_context)

            if matches >= max_matches:
                truncated = True
                stop_after_context = True

        elif after_remaining > 0:
            emit(lineno, line)
            after_remaining -= 1

            if stop_after_context and after_remaining == 0:
                break

        # Update before-context buffer after processing current line
        if before_context > 0:
            before.append((lineno, line))

    return ("\n".join(output) + ("\n" if output else "")), matches, truncated


async def grep(
    *,
    pattern: str,
    ignore_case: bool = False,
    regex: bool = False,
    line_numbers: bool = True,
    max_matches: int = 50,
    before_context: int = 0,
    after_context: int = 0,
) -> str:
    """
    Grep-like search over the analytics digest JSON file.

    Returns:
        A string similar to grep stdout output.
    """
    digest_path = _resolve_digest_path()
    matcher = _compile_matcher(pattern, ignore_case=ignore_case, regex=regex)

    # Read file as text and perform line-based searching.
    with digest_path.open("r", encoding="utf-8", errors="replace") as f:
        result, matches, truncated = _grep_lines(
            f,
            file_path=digest_path,
            matcher=matcher,
            with_line_numbers=line_numbers,
            max_matches=max_matches,
            before_context=before_context,
            after_context=after_context,
        )

    if matches == 0:
        return ""

    if truncated:
        result += f"-- truncated: max_matches={max_matches} --\n"
    return result

