
# RAG MCP

README объясняет, как подготовить данные статей, построить векторный индекс и запустить MCP‑сервер с тулом `search_articles`.

## Требования

- Python 3.10+
- Запущенный Ollama (`ollama serve`) и установленная модель `nomic-embed-text`
- Пакеты: `faiss-cpu`, `numpy`, `requests`, `beautifulsoup4`, `markdownify`, `tiktoken`, `mcp` (установите через `pip install ...`)

## Структура

- `articles.txt` — список ссылок на статьи (по одной в строке)
- `download_articles.py` — скачивает статьи и сохраняет в Markdown
- `build_vector_db.py` — строит FAISS‑индекс и метаданные
- `server.py` — MCP‑сервер со встроенным тулом `search_articles`

## Шаг 1. Скачать статьи в Markdown

```bash
python rag/download_articles.py rag/articles.txt arcticles/

```

- В `arcticles/` появятся `.md` файлы (каталог будет создан автоматически).
- В `articles.txt` можно указать URL или путь к локальному HTML.

## Шаг 2. Собрать векторную БД

Убедитесь, что Ollama запущена и модель загружена:

```bash
ollama pull nomic-embed-text
ollama serve  # если ещё не запущено

```

Постройте индекс и метаданные:

```bash
python rag/build_vector_db.py arcticles/ rag/articles.faiss \
  --meta-output rag/articles.faiss.meta.json \
  --chunk-size 500 --overlap 50 \
  --embedding-model nomic-embed-text \
  --ollama-url http://localhost:11434/api/embeddings

```

- `index_output` и `meta-output` должны лежать рядом с `server.py`, потому что сервер читает `articles.faiss` и `articles.faiss.meta.json` из каталога `rag/`.
- По умолчанию берутся расширения `.md` и `.markdown`, можно переопределить через `--extensions`.

## Шаг 3. Запустить MCP‑сервер

```bash
python rag/server.py

```

Сервер поднимается по stdio и предоставляет один тул:

- `search_articles` — параметры:
  - `query` (string, обязательный)
  - `top_k` (number, опционально, по умолчанию 5)

Результат: JSON с массивом объектов `{ score, source_path, chunk_idx, file_chunk_idx, text }`.

## Быстрая проверка

- Если сервер падает на старте, убедитесь, что файлы `rag/articles.faiss` и `rag/articles.faiss.meta.json` существуют и совпадает количество векторов и метаданных.
- Для детальной диагностики поднимите логирование: `python rag/server.py 2>&1 | tee server.log`.

