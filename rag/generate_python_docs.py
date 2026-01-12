#!/usr/bin/env python3
"""Generate Markdown docs for public Python APIs using LLM."""

import argparse
import asyncio
import fnmatch
import sys
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_logger, get_settings
from src.llm import GPTResponseParser, ModelName, ResponseProcessor, YandexLLMClient


SYSTEM_PROMPT = """
# ROLE
You are an expert Technical Writer and Code Analyst specializing in generating API documentation for Vector Database indexing (RAG pipelines).

# OBJECTIVE
Your task is to analyze Python source code and generate a concise, structured Markdown summary. The goal is to capture the **Public API contract** and the **semantic purpose** of the code. This output will be converted into embeddings, so precision and keyword density are crucial.

# INPUT FORMAT
You will receive raw Python code. The user might also provide the `File Path` at the beginning of the message. If the path is not provided, use `[Unknown Path]`.

# OUTPUT FORMAT (Markdown)
Follow this exact structure:

# File: `{file_path}`

## Module Summary
{A concise 2-3 sentence summary of what this entire file/module is responsible for. What domain does it cover?}

## classes & Functions

### `NameOfClassOrFunction`
**Description:** {What does this class/function do? What conceptual entity does it represent?}
**Public API:**
*   `method_name(args) -> return_type`: {Description of what this method does, what inputs it expects, and what it returns. Focus on the *business logic* or *utility*.}
*   `another_method(...)`: ...

*(Repeat for all top-level classes and functions).*

# CONSTRAINTS & RULES
1.  **Language:** English ONLY.
2.  **Scope:** Focus STRICTLY on the **Public API**.
    *   Ignore methods starting with `_` (underscore) unless they are critical for understanding the usage.
    *   Ignore magic methods like `__str__` or `__repr__` unless they contain custom complex logic.
    *   Always include `__init__` as it defines how to instantiate the class.
3.  **Detail Level:**
    *   Do not explain *how* the code works line-by-line (implementation details).
    *   Explain *what* the code achieves (interface contract).
    *   Capture Type Hints if available in the source (e.g., `-> List[str]`).
4.  **Tone:** Technical, objective, dense. No conversational filler ("Here is the summary...").

# EXAMPLE

**Input:**
`path: src/auth/manager.py`
```python
class AuthManager:
    '''Handles user sessions.'''
    def __init__(self, db_conn):
        self.db = db_conn

    def login(self, username: str, password_hash: str) -> bool:
        # logic...
        return True
    
    def _validate_token(self, token):
        # internal logic
        pass

    def logout(self, user_id: int) -> None:
        # logic...
        pass

"""

logger = get_logger(__name__)


def load_gitignore_patterns(root: Path) -> List[str]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    patterns: List[str] = []
    for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def is_ignored(rel_path: str, patterns: List[str]) -> bool:
    rel_posix = rel_path.replace("\\", "/")
    for pattern in patterns:
        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
    return False


def iter_py_files(root: Path, patterns: List[str]) -> Iterable[Path]:
    """Yield all .py files under root, excluding __pycache__ and ignored paths."""
    for path in root.rglob("*.py"):
        if any(part == "__pycache__" for part in path.parts):
            continue
        rel_path = str(path.relative_to(root))
        if rel_path.startswith("venv/") or rel_path == "venv":
            continue
        if is_ignored(rel_path, patterns):
            continue
        yield path


def build_user_message(rel_path: str, code: str) -> str:
    return (
        f"Файл: {rel_path}\n"
        "Сгенерируй лаконичную спецификацию публичных классов и функций.\n\n"
        "```python\n"
        f"{code}\n"
        "```"
    )


async def describe_file(
    client: YandexLLMClient,
    processor: ResponseProcessor,
    path: Path,
    rel_path: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    code = path.read_text(encoding="utf-8", errors="ignore")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": build_user_message(rel_path, code)},
    ]

    response = await client.send_prompt(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        tools=None,
        tool_choice="none",
    )
    return processor.extract_text(response)


async def generate_docs(
    project_root: Path,
    output_dir: Path,
    model: str,
    temperature: float,
    max_tokens: int,
) -> None:
    settings = get_settings()
    ignore_patterns = load_gitignore_patterns(project_root)
    ignore_patterns.append("venv/")
    client = YandexLLMClient(
        api_key=settings.eliza_token,
        base_url=settings.llm_base_url,
        temperature=temperature,
        model_name=model,
        max_tokens=max_tokens,
        ssl_verify=settings.ssl_verify,
    )
    processor = ResponseProcessor(parser=GPTResponseParser())

    try:
        tasks = []
        for path in iter_py_files(project_root, ignore_patterns):
            rel_path = str(path.relative_to(project_root))
            tasks.append((path, rel_path))

        for path, rel_path in tasks:
            logger.info("Processing %s", rel_path)
            try:
                doc = await describe_file(
                    client=client,
                    processor=processor,
                    path=path,
                    rel_path=rel_path,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:  # pragma: no cover - runtime safety
                logger.error("Failed to generate doc for %s: %s", rel_path, exc)
                doc = f"# {rel_path}\n\nОшибка генерации: {exc}"

            output_path = output_dir / Path(rel_path).with_suffix(".md")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(doc.strip() + "\n", encoding="utf-8")
    finally:
        await client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Markdown docs for public Python APIs using LLM."
    )
    parser.add_argument(
        "project_root", type=Path, help="Корневая папка проекта для обхода .py файлов."
    )
    parser.add_argument(
        "output_dir", type=Path, help="Папка, куда сохранять сгенерированные .md файлы."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=ModelName.GPT_4_O_MINI.value,
        help="Имя модели (по умолчанию gpt-4o-mini).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.4,
        help="Температура выборки для генерации.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1200,
        help="Лимит токенов для ответа модели.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not project_root.is_dir():
        logger.error("Project root does not exist: %s", project_root)
        return 1

    try:
        asyncio.run(
            generate_docs(
                project_root=project_root,
                output_dir=output_dir,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        )
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Generation failed: %s", exc, exc_info=True)
        return 1

    logger.info("Documentation generated in %s", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

