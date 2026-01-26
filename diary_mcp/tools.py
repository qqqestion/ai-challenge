import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Literal


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


EntryType = Literal["todo", "event", "note"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_unix_seconds(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def _iso_from_unix_seconds(ts: Optional[int]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=UTC).isoformat()


def _weekday_ru(dt: datetime) -> str:
    # Monday=0 .. Sunday=6
    mapping = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    return mapping[dt.weekday()]


def _normalize_tags(tags: Optional[list[str]]) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        if raw is None:
            continue
        tag = str(raw).strip()
        if not tag:
            continue
        # keep case as-is but dedupe case-insensitively
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized


def _get_diary_db_path() -> Path:
    # Separate DB (not rick_bot.db). Default: <repo-root>/diary.db
    env_path = os.getenv("DIARY_DB_PATH")
    if env_path:
        return Path(env_path).expanduser()
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "diary.db"


def _connect() -> sqlite3.Connection:
    db_path = _get_diary_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    # We keep schema local to this MCP and do not touch create_db.sql (separate DB file).
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL DEFAULT 0,
            entry_type TEXT NOT NULL CHECK (entry_type IN ('todo', 'event', 'note')),
            title TEXT,
            content TEXT,

            -- timestamps stored as unix seconds (UTC)
            created_ts INTEGER NOT NULL,
            updated_ts INTEGER NOT NULL,

            -- todo fields
            todo_due_ts INTEGER,
            todo_completed INTEGER NOT NULL DEFAULT 0 CHECK (todo_completed IN (0, 1)),
            todo_completed_ts INTEGER,

            -- calendar event fields
            event_start_ts INTEGER,
            event_end_ts INTEGER,

            -- note fields
            note_occurred_ts INTEGER
        );

        CREATE TABLE IF NOT EXISTS diary_tags (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            created_ts INTEGER NOT NULL,
            UNIQUE(user_id, name)
        );

        CREATE TABLE IF NOT EXISTS diary_entry_tags (
            entry_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, tag_id),
            FOREIGN KEY (entry_id) REFERENCES diary_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES diary_tags(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_diary_entries_user_type_created
            ON diary_entries(user_id, entry_type, created_ts);
        CREATE INDEX IF NOT EXISTS idx_diary_entries_user_event_start
            ON diary_entries(user_id, entry_type, event_start_ts);
        CREATE INDEX IF NOT EXISTS idx_diary_entries_user_todo_pending
            ON diary_entries(user_id, entry_type, todo_completed, todo_due_ts);
        CREATE INDEX IF NOT EXISTS idx_diary_tags_user_name
            ON diary_tags(user_id, name);
        """
    )
    conn.commit()


def _upsert_tags(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    tags: list[str],
    now_ts: int,
) -> list[int]:
    if not tags:
        return []

    tag_ids: list[int] = []
    for tag in tags:
        conn.execute(
            "INSERT OR IGNORE INTO diary_tags (user_id, name, created_ts) VALUES (?, ?, ?)",
            (user_id, tag, now_ts),
        )
        row = conn.execute(
            "SELECT id FROM diary_tags WHERE user_id = ? AND name = ?",
            (user_id, tag),
        ).fetchone()
        if row:
            tag_ids.append(int(row["id"]))
    return tag_ids


def _attach_tags(conn: sqlite3.Connection, *, entry_id: int, tag_ids: list[int]) -> None:
    if not tag_ids:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO diary_entry_tags (entry_id, tag_id) VALUES (?, ?)",
        [(entry_id, tag_id) for tag_id in tag_ids],
    )


def _fetch_entry_tags(conn: sqlite3.Connection, *, entry_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT t.name AS name
        FROM diary_entry_tags et
        JOIN diary_tags t ON t.id = et.tag_id
        WHERE et.entry_id = ?
        ORDER BY t.name ASC
        """,
        (entry_id,),
    ).fetchall()
    return [str(r["name"]) for r in rows]


@dataclass(frozen=True)
class DiaryEntryOut:
    id: int
    user_id: int
    entry_type: EntryType
    title: Optional[str]
    content: Optional[str]
    tags: list[str]

    created_at: str
    updated_at: str

    # todo
    todo_due_at: Optional[str] = None
    todo_completed: Optional[bool] = None
    todo_completed_at: Optional[str] = None

    # event
    event_start_at: Optional[str] = None
    event_end_at: Optional[str] = None
    weekday_ru: Optional[str] = None

    # note
    note_occurred_at: Optional[str] = None


def _row_to_entry(conn: sqlite3.Connection, row: sqlite3.Row) -> DiaryEntryOut:
    entry_id = int(row["id"])
    created_dt = datetime.fromtimestamp(int(row["created_ts"]), tz=UTC)
    updated_dt = datetime.fromtimestamp(int(row["updated_ts"]), tz=UTC)

    event_start_ts = row["event_start_ts"]
    weekday = None
    if event_start_ts is not None:
        weekday = _weekday_ru(datetime.fromtimestamp(int(event_start_ts), tz=UTC))

    return DiaryEntryOut(
        id=entry_id,
        user_id=int(row["user_id"]),
        entry_type=str(row["entry_type"]),  # type: ignore[assignment]
        title=row["title"],
        content=row["content"],
        tags=_fetch_entry_tags(conn, entry_id=entry_id),
        created_at=created_dt.isoformat(),
        updated_at=updated_dt.isoformat(),
        todo_due_at=_iso_from_unix_seconds(row["todo_due_ts"]),
        todo_completed=bool(row["todo_completed"]) if row["entry_type"] == "todo" else None,
        todo_completed_at=_iso_from_unix_seconds(row["todo_completed_ts"]),
        event_start_at=_iso_from_unix_seconds(event_start_ts),
        event_end_at=_iso_from_unix_seconds(row["event_end_ts"]),
        weekday_ru=weekday,
        note_occurred_at=_iso_from_unix_seconds(row["note_occurred_ts"]),
    )


async def diary_create_record(
    *,
    entry_type: EntryType,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[list[str]] = None,
    user_id: int = 0,
    todo_due_at: Optional[str] = None,
    event_start_at: Optional[str] = None,
    event_end_at: Optional[str] = None,
    note_occurred_at: Optional[str] = None,
) -> dict[str, Any]:
    """Create a diary record (todo/event/note) with tags (many-to-many)."""
    normalized_tags = _normalize_tags(tags)
    now = _utc_now()
    now_ts = _to_unix_seconds(now)

    def _parse_optional_iso(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return _to_unix_seconds(dt)

    todo_due_ts = _parse_optional_iso(todo_due_at)
    event_start_ts = _parse_optional_iso(event_start_at)
    event_end_ts = _parse_optional_iso(event_end_at)
    note_occurred_ts = _parse_optional_iso(note_occurred_at)

    # Convenience defaults: for notes, if occurred_at not provided, use "now"
    if entry_type == "note" and note_occurred_ts is None:
        note_occurred_ts = now_ts

    # Basic validation for events
    if entry_type == "event" and event_start_ts is None:
        return {"success": False, "error": "event_start_at is required for entry_type=event"}

    try:
        conn = _connect()
        _ensure_schema(conn)

        cur = conn.execute(
            """
            INSERT INTO diary_entries (
                user_id, entry_type, title, content,
                created_ts, updated_ts,
                todo_due_ts, todo_completed, todo_completed_ts,
                event_start_ts, event_end_ts,
                note_occurred_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?)
            """,
            (
                int(user_id),
                entry_type,
                title,
                content,
                now_ts,
                now_ts,
                todo_due_ts,
                event_start_ts,
                event_end_ts,
                note_occurred_ts,
            ),
        )
        entry_id = int(cur.lastrowid)

        tag_ids = _upsert_tags(conn, user_id=int(user_id), tags=normalized_tags, now_ts=now_ts)
        _attach_tags(conn, entry_id=entry_id, tag_ids=tag_ids)

        conn.commit()

        row = conn.execute("SELECT * FROM diary_entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return {"success": False, "error": "failed to fetch inserted entry"}

        entry_out = _row_to_entry(conn, row)
        return {"success": True, "entry": asdict(entry_out)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


async def diary_list_upcoming_events(
    *,
    days: int = 7,
    from_at: Optional[str] = None,
    tags: Optional[list[str]] = None,
    user_id: int = 0,
) -> dict[str, Any]:
    """List upcoming calendar events for the next N days (default 7)."""
    normalized_tags = _normalize_tags(tags)

    from_dt = _utc_now()
    if from_at:
        dt = datetime.fromisoformat(str(from_at).strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        from_dt = dt
    from_ts = _to_unix_seconds(from_dt)
    to_ts = _to_unix_seconds(from_dt + timedelta(days=int(days)))

    try:
        conn = _connect()
        _ensure_schema(conn)

        params: list[Any] = [int(user_id), from_ts, to_ts]
        tag_filter_sql = ""
        if normalized_tags:
            placeholders = ", ".join(["?"] * len(normalized_tags))
            tag_filter_sql = f"""
            AND e.id IN (
                SELECT et.entry_id
                FROM diary_entry_tags et
                JOIN diary_tags t ON t.id = et.tag_id
                WHERE t.user_id = ?
                AND t.name IN ({placeholders})
            )
            """
            params.append(int(user_id))
            params.extend(normalized_tags)

        rows = conn.execute(
            f"""
            SELECT e.*
            FROM diary_entries e
            WHERE e.user_id = ?
              AND e.entry_type = 'event'
              AND e.event_start_ts IS NOT NULL
              AND e.event_start_ts >= ?
              AND e.event_start_ts < ?
              {tag_filter_sql}
            ORDER BY e.event_start_ts ASC
            """,
            tuple(params),
        ).fetchall()

        events = [asdict(_row_to_entry(conn, row)) for row in rows]
        return {"success": True, "from_at": from_dt.isoformat(), "to_at": _iso_from_unix_seconds(to_ts), "events": events}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


async def diary_list_pending_todos(
    *,
    tags: Optional[list[str]] = None,
    user_id: int = 0,
) -> dict[str, Any]:
    """List pending (not completed) todo entries."""
    normalized_tags = _normalize_tags(tags)

    try:
        conn = _connect()
        _ensure_schema(conn)

        params: list[Any] = [int(user_id)]
        tag_filter_sql = ""
        if normalized_tags:
            placeholders = ", ".join(["?"] * len(normalized_tags))
            tag_filter_sql = f"""
            AND e.id IN (
                SELECT et.entry_id
                FROM diary_entry_tags et
                JOIN diary_tags t ON t.id = et.tag_id
                WHERE t.user_id = ?
                AND t.name IN ({placeholders})
            )
            """
            params.append(int(user_id))
            params.extend(normalized_tags)

        rows = conn.execute(
            f"""
            SELECT e.*
            FROM diary_entries e
            WHERE e.user_id = ?
              AND e.entry_type = 'todo'
              AND e.todo_completed = 0
              {tag_filter_sql}
            ORDER BY
              CASE WHEN e.todo_due_ts IS NULL THEN 1 ELSE 0 END ASC,
              e.todo_due_ts ASC,
              e.created_ts ASC
            """,
            tuple(params),
        ).fetchall()

        todos = [asdict(_row_to_entry(conn, row)) for row in rows]
        return {"success": True, "todos": todos}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass

