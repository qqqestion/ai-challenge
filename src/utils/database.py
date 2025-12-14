"""SQLite database manager for persistent chat history and user settings."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class UserSettings:
    """User settings data structure."""
    user_id: int
    model: str = 'gpt-4o-mini'
    temperature: float = 0.3
    summarization_enabled: bool = True


@dataclass
class Message:
    """Message data structure."""
    id: Optional[int]
    user_id: int
    role: str
    content: str
    created_at: datetime


@dataclass
class UsageStats:
    """Usage statistics data structure."""
    user_id: int
    chat_input_tokens: int = 0
    chat_output_tokens: int = 0
    chat_cost: float = 0.0
    requests_count: int = 0
    summarization_count: int = 0
    summarization_input_tokens: int = 0
    summarization_output_tokens: int = 0
    summarization_cost: float = 0.0


class DatabaseManager:
    """SQLite database manager for bot persistence."""

    def __init__(self, db_path: str = "rick_bot.db"):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
        logger.info(f"DatabaseManager initialized with path: {db_path}")

    async def initialize(self):
        """Initialize database connection and create tables if needed."""
        try:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Allow access from multiple threads
                timeout=30.0
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            self._connection.execute("PRAGMA synchronous=NORMAL")  # Balance performance/safety
            self._connection.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints

            # Check if database is already initialized
            cursor = self._connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                logger.info("Database already initialized, skipping table creation")
            else:
                # Create tables if they don't exist
                await self._create_tables()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def _execute_query(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """Execute a query with error handling."""
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            return self._connection.execute(query, params)
        except Exception as e:
            logger.error(f"Database query failed: {query} with params {params}")
            raise

    def _execute_many(self, query: str, params_list: List[Tuple]) -> sqlite3.Cursor:
        """Execute multiple queries with error handling."""
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            return self._connection.executemany(query, params_list)
        except Exception as e:
            logger.error(f"Database batch query failed: {query}")
            raise

    async def _create_tables(self):
        """Create database tables from schema."""
        schema_path = Path(__file__).parent.parent.parent / "create_db.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Split schema into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

        for statement in statements:
            if statement:
                try:
                    self._execute_query(statement)
                except sqlite3.OperationalError as e:
                    error_msg = str(e)
                    # Check if it's the expected "table already exists" error
                    if "already exists" in error_msg:
                        logger.debug(f"Table already exists, skipping: {statement.split()[2] if len(statement.split()) > 2 else 'unknown'}")
                        continue
                    # For INSERT statements, check if it's about duplicate key
                    elif "UNIQUE constraint failed" in error_msg or "PRIMARY KEY constraint failed" in error_msg:
                        logger.debug(f"Record already exists, skipping INSERT: {statement[:50]}...")
                        continue
                    else:
                        # Re-raise unexpected errors
                        logger.error(f"Unexpected database error: {e}")
                        raise

        self._connection.commit()
        logger.info("Database tables created/verified")

    # User management methods

    async def get_or_create_user(self, user_id: int) -> int:
        """Get or create user record.

        Args:
            user_id: Telegram user ID

        Returns:
            Internal user ID
        """
        # Check if user exists
        cursor = self._execute_query(
            "SELECT id FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            return row['id']

        # Create new user
        cursor = self._execute_query(
            "INSERT INTO users (user_id, last_activity, created_at, updated_at) VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user_id,)
        )
        self._connection.commit()
        logger.info(f"Created new user record for user_id: {user_id}")
        return cursor.lastrowid

    async def get_user_settings(self, user_id: int) -> UserSettings:
        """Get user settings, creating defaults if not exists.

        Args:
            user_id: Telegram user ID

        Returns:
            UserSettings object
        """
        cursor = self._execute_query(
            "SELECT model, temperature, summarization_enabled FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            return UserSettings(
                user_id=user_id,
                model=row['model'],
                temperature=row['temperature'],
                summarization_enabled=bool(row['summarization_enabled'])
            )

        # Create default settings
        await self.save_user_settings(UserSettings(user_id=user_id))
        return UserSettings(user_id=user_id)

    async def save_user_settings(self, settings: UserSettings):
        """Save or update user settings.

        Args:
            settings: UserSettings object
        """
        self._execute_query(
            """INSERT OR REPLACE INTO user_settings
               (user_id, model, temperature, summarization_enabled)
               VALUES (?, ?, ?, ?)""",
            (settings.user_id, settings.model, settings.temperature, settings.summarization_enabled)
        )
        self._connection.commit()
        logger.debug(f"Saved settings for user {settings.user_id}")

    # Message management methods

    async def save_message(self, message: Message) -> int:
        """Save a message to database.

        Args:
            message: Message object

        Returns:
            Message ID
        """
        cursor = self._execute_query(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (message.user_id, message.role, message.content, message.created_at)
        )
        self._connection.commit()
        return cursor.lastrowid

    async def get_user_messages(self, user_id: int, limit: int = 100) -> List[Message]:
        """Get recent messages for user.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to return

        Returns:
            List of Message objects
        """
        cursor = self._execute_query(
            """SELECT id, user_id, role, content, created_at
               FROM messages
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit)
        )

        messages = []
        for row in cursor.fetchall():
            messages.append(Message(
                id=row['id'],
                user_id=row['user_id'],
                role=row['role'],
                content=row['content'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))

        # Return in chronological order (oldest first)
        return list(reversed(messages))

    async def delete_summarized_messages(self, user_id: int, summarization_message_id: int):
        """Delete messages that were summarized.

        Args:
            user_id: Telegram user ID
            summarization_message_id: ID of the summarization message to keep
        """
        # Delete all messages for user except the summarization message
        self._execute_query(
            "DELETE FROM messages WHERE user_id = ? AND id != ?",
            (user_id, summarization_message_id)
        )
        self._connection.commit()
        logger.info(f"Deleted summarized messages for user {user_id}, kept summarization message {summarization_message_id}")

    async def delete_all_messages(self, user_id: int):
        """Delete all messages for a user (used for reset).

        Args:
            user_id: Telegram user ID
        """
        self._execute_query(
            "DELETE FROM messages WHERE user_id = ?",
            (user_id,)
        )
        self._connection.commit()
        logger.info(f"Deleted all messages for user {user_id}")

    async def reset_usage_stats(self, user_id: int):
        """Reset usage statistics for a user to zero.

        Args:
            user_id: Telegram user ID
        """
        # Use INSERT OR REPLACE to ensure the row exists and is reset to zero
        self._execute_query(
            """INSERT OR REPLACE INTO usage_stats
               (user_id, chat_input_tokens, chat_output_tokens, chat_cost, requests_count,
                summarization_count, summarization_input_tokens, summarization_output_tokens, summarization_cost)
               VALUES (?, 0, 0, 0.0, 0, 0, 0, 0, 0.0)""",
            (user_id,)
        )
        self._connection.commit()
        logger.info(f"Reset usage statistics for user {user_id}")

    # Usage statistics methods

    async def get_usage_stats(self, user_id: int) -> UsageStats:
        """Get usage statistics for user.

        Args:
            user_id: Telegram user ID

        Returns:
            UsageStats object
        """
        cursor = self._execute_query(
            """SELECT chat_input_tokens, chat_output_tokens, chat_cost, requests_count,
                      summarization_count, summarization_input_tokens, summarization_output_tokens, summarization_cost
               FROM usage_stats WHERE user_id = ?""",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            return UsageStats(
                user_id=user_id,
                chat_input_tokens=row['chat_input_tokens'],
                chat_output_tokens=row['chat_output_tokens'],
                chat_cost=row['chat_cost'],
                requests_count=row['requests_count'],
                summarization_count=row['summarization_count'],
                summarization_input_tokens=row['summarization_input_tokens'],
                summarization_output_tokens=row['summarization_output_tokens'],
                summarization_cost=row['summarization_cost']
            )

        # Return empty stats
        return UsageStats(user_id=user_id)

    async def update_usage_stats(self, stats: UsageStats):
        """Update usage statistics for user.

        Args:
            stats: UsageStats object
        """
        self._execute_query(
            """INSERT OR REPLACE INTO usage_stats
               (user_id, chat_input_tokens, chat_output_tokens, chat_cost, requests_count,
                summarization_count, summarization_input_tokens, summarization_output_tokens, summarization_cost)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (stats.user_id, stats.chat_input_tokens, stats.chat_output_tokens, stats.chat_cost,
             stats.requests_count, stats.summarization_count, stats.summarization_input_tokens,
             stats.summarization_output_tokens, stats.summarization_cost)
        )
        self._connection.commit()
        logger.debug(f"Updated usage stats for user {stats.user_id}")

    async def increment_chat_usage(self, user_id: int, input_tokens: int, output_tokens: int, cost: float):
        """Increment chat usage statistics.

        Args:
            user_id: Telegram user ID
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of the request
        """
        current_stats = await self.get_usage_stats(user_id)
        current_stats.chat_input_tokens += input_tokens
        current_stats.chat_output_tokens += output_tokens
        current_stats.chat_cost += cost
        current_stats.requests_count += 1
        await self.update_usage_stats(current_stats)

    async def increment_summarization_usage(self, user_id: int, input_tokens: int, output_tokens: int, cost: float):
        """Increment summarization usage statistics.

        Args:
            user_id: Telegram user ID
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of the request
        """
        current_stats = await self.get_usage_stats(user_id)
        current_stats.summarization_input_tokens += input_tokens
        current_stats.summarization_output_tokens += output_tokens
        current_stats.summarization_cost += cost
        current_stats.summarization_count += 1
        await self.update_usage_stats(current_stats)

    # Cleanup methods

    async def cleanup_old_states(self, hours: int = 24):
        """Clean up old user states (for compatibility with StateManager).

        Args:
            hours: Hours of inactivity before cleanup
        """
        # This method exists for compatibility but database cleanup
        # should be handled differently (e.g., scheduled job)
        # For now, just log that cleanup is not needed
        logger.debug(f"Database cleanup requested for {hours}h inactivity - not implemented")

    async def get_active_users_count(self) -> int:
        """Get count of active users.

        Returns:
            Number of users with recent activity
        """
        cursor = self._execute_query(
            "SELECT COUNT(*) as count FROM users WHERE last_activity > datetime('now', '-24 hours')"
        )
        row = cursor.fetchone()
        return row['count'] if row else 0
