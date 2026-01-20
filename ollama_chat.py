#!/usr/bin/env python3

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OllamaConfig:
    host: str
    port: int
    model: str
    timeout_s: float

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class OllamaClient:
    def __init__(self, config: OllamaConfig) -> None:
        self._config = config

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "stream": False,
        }
        req = Request(
            url=f"{self._config.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=self._config.timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        text = data.get("response")
        if not isinstance(text, str):
            raise ValueError("Unexpected Ollama response: missing 'response' field")
        return text

    def close(self) -> None:
        return None


def _parse_args(argv: list[str]) -> OllamaConfig:
    parser = argparse.ArgumentParser(
        description="Simple CLI chat with local Ollama (no history).",
    )
    parser.add_argument("--host", default="localhost", help="Ollama host (default: localhost)")
    parser.add_argument("--port", type=int, default=11434, help="Ollama port (default: 11434)")
    parser.add_argument("--model", default="gpt-oss:20b", help="Ollama model name")
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Request timeout in seconds (default: 120)",
    )
    args = parser.parse_args(argv)

    return OllamaConfig(
        host=args.host,
        port=args.port,
        model=args.model,
        timeout_s=args.timeout,
    )


def main(argv: list[str]) -> int:
    config = _parse_args(argv)
    client = OllamaClient(config)

    try:
        while True:
            try:
                user_text = input("> ").strip()
            except EOFError:
                sys.stderr.write("\n")
                return 0
            except KeyboardInterrupt:
                sys.stderr.write("\n")
                return 0

            if not user_text:
                continue
            if user_text in {"/exit", "/quit"}:
                return 0

            try:
                answer = client.generate(user_text)
            except URLError:
                sys.stderr.write(
                    f"Ошибка: не удалось подключиться к Ollama по {config.base_url}.\n"
                    "Убедись, что Ollama запущена и порт доступен.\n"
                )
                continue
            except TimeoutError:
                sys.stderr.write(
                    f"Ошибка: таймаут запроса ({config.timeout_s:.0f}s). "
                    "Попробуй увеличить --timeout.\n"
                )
                continue
            except HTTPError as e:
                sys.stderr.write(f"Ошибка Ollama HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}\n")
                continue
            except ValueError as e:
                sys.stderr.write(f"Ошибка: неожиданный ответ от Ollama: {e}\n")
                continue

            sys.stdout.write(answer.rstrip() + "\n")
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


