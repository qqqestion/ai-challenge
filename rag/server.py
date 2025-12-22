#!/usr/bin/env python3
"""
RAG MCP Server.

Provides a single tool `search_articles` to perform vector similarity search
over the prebuilt FAISS index stored in this directory.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import requests

try:
    import faiss
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The 'faiss-cpu' package is required to run this server.") from exc

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


logger = logging.getLogger("rag-mcp-server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

CURRENT_DIR = Path(__file__).parent
INDEX_PATH = CURRENT_DIR / "articles.faiss"
META_PATH = CURRENT_DIR / "articles.faiss.meta.json"

DEFAULT_EMBED_URL = "http://localhost:11434/api/embeddings"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_TOP_K = 5

app = Server("rag-mcp-server")


def _load_index_and_meta() -> tuple[faiss.Index, list[dict]]:
    if not INDEX_PATH.is_file():
        raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")
    if not META_PATH.is_file():
        raise FileNotFoundError(f"Metadata file not found: {META_PATH}")

    logger.info("Loading FAISS index from %s", INDEX_PATH)
    index = faiss.read_index(str(INDEX_PATH))

    logger.info("Loading metadata from %s", META_PATH)
    metadata = json.loads(META_PATH.read_text(encoding="utf-8"))

    if len(metadata) != index.ntotal:
        raise ValueError(
            f"Metadata count ({len(metadata)}) does not match index vectors ({index.ntotal})"
        )

    return index, metadata


INDEX, METADATA = _load_index_and_meta()
EMBED_DIM = INDEX.d


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _embed_query(query: str) -> np.ndarray:
    payload = {"model": DEFAULT_EMBED_MODEL, "input": query}
    response = requests.post(DEFAULT_EMBED_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Unexpected embeddings response format")
    vector = np.array(embedding, dtype="float32")
    if vector.ndim != 1:
        raise ValueError("Embedding vector must be 1-D")
    if vector.shape[0] != EMBED_DIM:
        raise ValueError(
            f"Embedding dim mismatch: got {vector.shape[0]}, expected {EMBED_DIM}"
        )
    return _normalize(vector.reshape(1, -1))


TOOLS = [
    Tool(
        name="search_articles",
        description="Vector search in article chunks. Returns top matches with full chunk text.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query text to search for similar content.",
                },
                "top_k": {
                    "type": "number",
                    "description": "Number of results to return (default 5).",
                    "default": DEFAULT_TOP_K,
                },
            },
            "required": ["query"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    logger.debug("list_tools() called")
    return TOOLS


def _search_articles(query: str, top_k: int) -> list[dict]:
    top_k = max(1, min(top_k, INDEX.ntotal))

    query_vec = _embed_query(query)
    scores, idxs = INDEX.search(query_vec, top_k)

    results: list[dict] = []
    for score, idx in zip(scores[0], idxs[0]):
        meta = METADATA[idx]
        results.append(
            {
                "score": float(score),
                "source_path": meta.get("source_path"),
                "chunk_idx": meta.get("chunk_idx"),
                "file_chunk_idx": meta.get("file_chunk_idx"),
                "text": meta.get("text"),
            }
        )
    return results


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    logger.info("call_tool invoked: %s", name)
    logger.debug("Arguments: %s", arguments)

    try:
        if name == "search_articles":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError("Field 'query' must be a non-empty string")
            top_k = arguments.get("top_k", DEFAULT_TOP_K)
            if not isinstance(top_k, (int, float)):
                raise ValueError("Field 'top_k' must be a number")
            results = _search_articles(query.strip(), int(top_k))
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [
            TextContent(
                type="text",
                text=json.dumps({"results": results}, ensure_ascii=False, indent=2),
            )
        ]

    except Exception as e:
        logger.error("Error executing tool %s: %s", name, e, exc_info=True)
        return [TextContent(type="text", text=f"Error: {e}")]


async def main():
    try:
        logger.info("=" * 60)
        logger.info("Starting RAG MCP Server")
        logger.info("Index path: %s", INDEX_PATH)
        logger.info("Metadata path: %s", META_PATH)
        logger.info("Vectors: %d", INDEX.ntotal)
        logger.info("=" * 60)

        async with stdio_server() as (read_stream, write_stream):
            init_options = app.create_initialization_options()
            await app.run(read_stream, write_stream, init_options)

    except Exception as e:  # pragma: no cover
        logger.error("Fatal error: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error("Server crashed: %s", e, exc_info=True)
        raise

