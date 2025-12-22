import argparse
import logging
import pathlib
import re
import sys
import unicodedata
from typing import Iterable, Optional
from urllib.parse import urlparse

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The 'requests' package is required to run this script.") from exc

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The 'beautifulsoup4' package is required to run this script.") from exc

try:
    from markdownify import markdownify as md
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The 'markdownify' package is required to run this script.") from exc


def is_url(source: str) -> bool:
    parsed = urlparse(source.strip())
    return parsed.scheme in {"http", "https"}


def read_sources(list_path: pathlib.Path) -> Iterable[str]:
    with list_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            yield line


def fetch_html(source: str) -> str:
    if is_url(source):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return response.text
    path = pathlib.Path(source).expanduser().resolve(strict=True)
    return path.read_text(encoding="utf-8")


def extract_title(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return None


def extract_main_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    candidates = [
        soup.select_one("#post-content-body"),
        soup.select_one("article"),
        soup.select_one("main"),
        soup.select_one(".tm-article-presenter__body"),
        soup.select_one(".tm-article-body"),
        soup.select_one(".article-formatted-body"),
        soup.select_one('[data-qa="article-body"]'),
        soup.body,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return html


def html_to_markdown(html_fragment: str) -> str:
    try:
        return md(html_fragment, heading_style="ATX")
    except Exception:
        pass

    try:
        soup = BeautifulSoup(html_fragment, "html.parser")
        return soup.get_text("\n")
    except Exception:
        return html_fragment


def slugify(text: str, fallback: str = "article") -> str:
    normalized = unicodedata.normalize("NFKD", text).strip().lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"[^\w\-]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    if not normalized:
        normalized = re.sub(r"[^\w\-]+", "-", fallback).strip("-") or "article"
    return normalized[:80]


def build_filename(title: Optional[str], source: str) -> str:
    if title:
        base = slugify(title)
    else:
        parsed = urlparse(source)
        if parsed.path:
            base = slugify(pathlib.Path(parsed.path).stem or "article")
        else:
            base = slugify(pathlib.Path(source).stem or "article")
    return f"{base or 'article'}.md"


def save_markdown(output_dir: pathlib.Path, filename: str, markdown: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    content = markdown.strip() + "\n"
    (output_dir / filename).write_text(content, encoding="utf-8")


def process_source(source: str, output_dir: pathlib.Path) -> None:
    logging.info("Processing: %s", source)
    html = fetch_html(source)
    title = extract_title(html)
    main_html = extract_main_content(html)
    markdown = html_to_markdown(main_html)
    filename = build_filename(title, source)
    save_markdown(output_dir, filename, markdown)
    logging.info("Saved: %s", filename)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download articles from list (URLs or local HTML files) and save as Markdown."
    )
    parser.add_argument("list_file", type=pathlib.Path, help="Path to file with article URLs/paths (one per line).")
    parser.add_argument("output_dir", type=pathlib.Path, help="Directory to store resulting Markdown files.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    try:
        sources = list(read_sources(args.list_file))
    except FileNotFoundError as err:
        logging.error("List file not found: %s", err)
        return 1
    if not sources:
        logging.warning("No sources found in %s", args.list_file)
        return 0

    for source in sources:
        try:
            process_source(source, args.output_dir)
        except Exception as err:  # pragma: no cover
            logging.error("Failed to process %s: %s", source, err)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

