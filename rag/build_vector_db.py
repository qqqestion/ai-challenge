import argparse
import json
import logging
import pathlib
import sys
import time
from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence

import numpy as np
import requests

try:
    import faiss
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The 'faiss-cpu' package is required to run this script.") from exc

try:
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None


DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 50
DEFAULT_EXTENSIONS = {".md", ".markdown"}
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/embeddings"


@dataclass(frozen=True)
class ChunkMeta:
    source_path: str
    chunk_idx: int
    file_chunk_idx: int
    text: str


def build_token_len() -> Callable[[str], int]:
    """Return a function that counts tokens for a given text."""
    if tiktoken is None:
        logging.warning("tiktoken not found, falling back to whitespace token counting.")

        def fallback(text: str) -> int:
            return max(1, len(text.split()))

        return fallback

    enc = tiktoken.get_encoding("gpt2")

    def count_tokens(text: str) -> int:
        return len(enc.encode(text))

    return count_tokens


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    token_len: Callable[[str], int] | None = None,
) -> Iterable[str]:
    """Split text into chunks with token-based limit and overlap, avoiding word cuts."""
    if token_len is None:
        token_len = build_token_len()

    words: List[str] = text.split()
    if not words:
        return []

    current_words: List[str] = []
    current_tokens = 0

    for word in words:
        word_tokens = token_len(word)
        if current_tokens + word_tokens > chunk_size and current_words:
            yield " ".join(current_words)

            if overlap > 0:
                retained: List[str] = []
                retained_tokens = 0
                for w in reversed(current_words):
                    w_len = token_len(w)
                    if retained_tokens + w_len > overlap:
                        break
                    retained.insert(0, w)
                    retained_tokens += w_len
                current_words = retained
                current_tokens = retained_tokens
            else:
                current_words = []
                current_tokens = 0

        current_words.append(word)
        current_tokens += word_tokens

    if current_words:
        yield " ".join(current_words)


def iter_markdown_files(root: pathlib.Path, extensions: set[str]) -> Iterable[pathlib.Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def read_markdown(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def embed_text(
    text: str,
    model: str,
    url: str,
    timeout: int = 60,
) -> List[float]:
    payload = {"model": model, "prompt": text}
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Unexpected embeddings response format")
    if len(embedding) == 0:
        raise ValueError("Received empty embedding vector")
    return embedding


def normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def save_metadata(meta: Sequence[ChunkMeta], meta_path: pathlib.Path) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = [meta.__dict__ for meta in meta]
    meta_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build FAISS vector index from markdown articles with Ollama embeddings."
    )
    parser.add_argument("input_dir", type=pathlib.Path, help="Directory with markdown articles.")
    parser.add_argument("index_output", type=pathlib.Path, help="Path to save FAISS index file.")
    parser.add_argument(
        "--meta-output",
        type=pathlib.Path,
        help="Path to save metadata JSON (default: <index_output>.meta.json).",
    )
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in tokens.")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="Overlap in tokens between chunks.")
    parser.add_argument(
        "--extensions",
        type=str,
        default=",".join(sorted(DEFAULT_EXTENSIONS)),
        help="Comma-separated list of markdown extensions to include.",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=DEFAULT_OLLAMA_URL,
        help="Ollama embeddings endpoint.",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
        help="Ollama embedding model name.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    input_dir: pathlib.Path = args.input_dir.expanduser().resolve()
    index_output: pathlib.Path = args.index_output.expanduser().resolve()
    meta_output: pathlib.Path = (
        args.meta_output.expanduser().resolve()
        if args.meta_output
        else index_output.with_suffix(index_output.suffix + ".meta.json")
    )
    extensions = {ext.lower() for ext in args.extensions.split(",") if ext.strip()}

    if not input_dir.is_dir():
        logging.error("Input directory not found: %s", input_dir)
        return 1

    files = list(iter_markdown_files(input_dir, extensions))
    if not files:
        logging.error("No markdown files found under %s (extensions: %s)", input_dir, extensions)
        return 1

    logging.info("Found %d markdown files, starting chunking...", len(files))

    token_len = build_token_len()
    all_chunks: list[str] = []
    metadata: list[ChunkMeta] = []

    chunk_idx = 0
    for file_idx, file_path in enumerate(sorted(files)):
        text = read_markdown(file_path)
        file_chunk_idx = 0
        for chunk in chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap, token_len=token_len):
            all_chunks.append(chunk)
            metadata.append(
                ChunkMeta(
                    source_path=str(file_path),
                    chunk_idx=chunk_idx,
                    file_chunk_idx=file_chunk_idx,
                    text=chunk,
                )
            )
            chunk_idx += 1
            file_chunk_idx += 1

    logging.info("Prepared %d chunks, requesting embeddings from Ollama...", len(all_chunks))

    embeddings: list[list[float]] = []
    start_time = time.time()
    for idx, chunk in enumerate(all_chunks):
        if idx % 50 == 0 and idx > 0:
            logging.info("Embedded %d/%d chunks...", idx, len(all_chunks))
        emb = embed_text(chunk, model=args.embedding_model, url=args.ollama_url)
        embeddings.append(emb)
    elapsed = time.time() - start_time
    logging.info("Completed embedding generation in %.2f seconds.", elapsed)

    if not embeddings:
        logging.error("No embeddings generated.")
        return 1

    dim = len(embeddings[0])
    matrix = np.array(embeddings, dtype="float32")
    if matrix.shape[1] != dim:
        logging.error("Embedding dimensions are inconsistent.")
        return 1

    matrix = normalize_embeddings(matrix)

    index = faiss.IndexFlatIP(dim)
    index.add(matrix)

    index_output.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_output))
    save_metadata(metadata, meta_output)

    logging.info("Index saved to %s", index_output)
    logging.info("Metadata saved to %s", meta_output)
    logging.info("Total vectors: %d", len(embeddings))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


