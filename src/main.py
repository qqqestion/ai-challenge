"""Main application entry point."""

import asyncio
import signal
from pathlib import Path
from datetime import time

from .config import get_settings, setup_logger, get_logger
from .llm import YandexLLMClient, ResponseProcessor
from .bot import RickBot, StateManager
from .bot.llm_integration import LLMIntegration
from .bot.mcp_manager import MCPManager
from .bot.daily_summary_manager import DailySummaryManager
from .utils.database import DatabaseManager

# Global references for cleanup
_bot_instance = None
_llm_client = None
_db_manager = None
_mcp_managers = []


async def initialize_application():
    """Initialize all application components.

    Returns:
        Tuple of (bot, llm_client, db_manager, mcp_managers, daily_summary_manager) instances
    """
    # Load settings
    settings = get_settings()

    # Setup logging
    setup_logger(
        name="rick_bot",
        log_level=settings.log_level,
        log_to_file=True,
        log_dir="logs"
    )

    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Rick Sanchez Bot - Starting initialization")
    logger.info("=" * 60)

    # Initialize LLM client
    logger.info("Initializing Yandex LLM client...")
    llm_client = YandexLLMClient(
        api_key=settings.eliza_token,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        ssl_verify=settings.ssl_verify,
        timeout=60.0
    )
    logger.info("✓ LLM client initialized")

    # Initialize response processor
    response_processor = ResponseProcessor()

    # Initialize database manager
    logger.info("Initializing database manager...")
    db_manager = DatabaseManager(db_path="rick_bot.db")
    await db_manager.initialize()
    logger.info("✓ Database manager initialized")

    # Initialize state manager
    logger.info("Initializing state manager...")
    state_manager = StateManager(
        db_manager=db_manager,
        cleanup_hours=settings.user_state_cleanup_hours
    )
    logger.info("✓ State manager initialized")

    # Initialize MCP managers (optional)
    mcp_managers: list[MCPManager] = []
    github_mcp_manager: MCPManager | None = None
    report_mcp_manager: MCPManager | None = None
    android_mcp_manager: MCPManager | None = None

    async def _init_manager(path: Path, name: str) -> MCPManager | None:
        try:
            logger.info("Initializing MCP manager: %s", name)
            manager = MCPManager(server_script_path=str(path))
            try:
                if await manager.initialize():
                    logger.info("✓ MCP manager initialized: %s", name)
                    return manager
                logger.warning("⚠ MCP manager initialization failed: %s", name)
            except asyncio.TimeoutError:
                logger.warning("⚠ MCP manager initialization timed out: %s", name)
            except Exception as init_error:
                logger.warning(
                    "⚠ MCP manager initialization error (%s): %s",
                    name,
                    init_error,
                )
        except Exception as e:
            logger.warning("⚠ MCP manager creation error (%s): %s", name, e)
        return None

    if settings.mcp_enabled:
        base_dir = Path(__file__).resolve().parent.parent
        github_path = base_dir / "github_mcp" / "server.py"
        report_path = base_dir / "report_mcp" / "server.py"
        android_path = base_dir / "android_mcp" / "server.py"

        github_mcp_manager = await _init_manager(github_path, "github_mcp")
        report_mcp_manager = await _init_manager(report_path, "report_mcp")
        android_mcp_manager = await _init_manager(android_path, "android_mcp")

        for manager in (github_mcp_manager, report_mcp_manager, android_mcp_manager):
            if manager:
                mcp_managers.append(manager)
    else:
        logger.info("MCP integration disabled (set MCP_ENABLED=true to enable)")

    # Initialize LLM integration
    logger.info("Initializing LLM integration...")
    llm_integration = LLMIntegration(
        llm_client=llm_client,
        state_manager=state_manager,
        response_processor=response_processor,
        mcp_managers=mcp_managers
    )
    logger.info("✓ LLM integration initialized")

    # Initialize bot
    logger.info("Initializing Telegram bot...")
    bot = RickBot(
        settings=settings,
        state_manager=state_manager,
        llm_integration=llm_integration
    )
    logger.info("✓ Bot initialized")

    # Initialize DailySummaryManager (only if GitHub MCP is available)
    daily_summary_manager = None
    if github_mcp_manager and github_mcp_manager.is_initialized:
        logger.info("Initializing DailySummaryManager...")
        daily_summary_manager = DailySummaryManager(
            mcp_manager=github_mcp_manager,
            llm_integration=llm_integration,
            db_manager=db_manager,
            bot=bot.application.bot
        )
        
        # Add to bot_data for access from handlers
        bot.application.bot_data["daily_summary_manager"] = daily_summary_manager
        logger.info("✓ DailySummaryManager initialized")
    else:
        logger.warning("⚠ DailySummaryManager not initialized (MCP not available)")

    logger.info("=" * 60)
    logger.info("Initialization complete!")
    logger.info("=" * 60)

    return bot, llm_client, db_manager, mcp_managers, daily_summary_manager


async def cleanup_application(
    bot: RickBot,
    llm_client: YandexLLMClient,
    db_manager: DatabaseManager,
    mcp_managers: list[MCPManager] | None = None,
    daily_summary_manager: DailySummaryManager = None,
):
    """Cleanup application resources.

    Args:
        bot: Rick bot instance
        llm_client: LLM client instance
        db_manager: Database manager instance
        mcp_managers: MCP manager instances (optional)
        daily_summary_manager: Daily summary manager instance (optional)
    """
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Starting cleanup...")
    logger.info("=" * 60)

    try:
        # Stop bot
        logger.info("Stopping bot...")
        await bot.stop()
        logger.info("✓ Bot stopped")

        # Close LLM client
        logger.info("Closing LLM client...")
        await llm_client.close()
        logger.info("✓ LLM client closed")

        # Close MCP managers
        if mcp_managers:
            for manager in mcp_managers:
                try:
                    logger.info("Closing MCP manager...")
                    await manager.cleanup()
                    logger.info("✓ MCP manager closed")
                except Exception as e:
                    logger.warning(f"Error closing MCP manager: {e}")

        # Close database connection
        logger.info("Closing database connection...")
        await db_manager.close()
        logger.info("✓ Database connection closed")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("Cleanup complete. Goodbye!")
    logger.info("=" * 60)


async def main():
    """Main application entry point."""
    global _bot_instance, _llm_client, _db_manager, _mcp_managers

    logger = get_logger()

    try:
        # Initialize
        bot, llm_client, db_manager, mcp_managers, daily_summary_manager = await initialize_application()
        _bot_instance = bot
        _llm_client = llm_client
        _db_manager = db_manager
        _mcp_managers = mcp_managers

        # Setup JobQueue for daily summaries
        if daily_summary_manager:
            logger.info("=" * 60)
            logger.info("Setting up JobQueue for daily summaries")
            logger.info("=" * 60)
            
            job_queue = bot.application.job_queue
            
            # Schedule daily summary at 06:00 UTC (09:00 MSK)
            job_queue.run_daily(
                daily_summary_manager.send_all_daily_summaries,
                time=time(hour=6, minute=0, second=0),
                days=(0, 1, 2, 3, 4, 5, 6),  # Every day
                name='daily_github_summary'
            )
            
            logger.info("✓ Daily summary job scheduled for 06:00 UTC (09:00 MSK)")
            logger.info("=" * 60)
        else:
            logger.info("Daily summary job not scheduled (manager not initialized)")

        # Start bot
        await bot.start()

        # Keep running until interrupted
        logger.info("Bot is running. Press Ctrl+C to stop.")

        # Wait for stop signal
        stop_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            stop_event.set()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Wait for stop event
        await stop_event.wait()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt (Ctrl+C)")
    except Exception as e:
        # Check for specific error types
        error_message = str(e)

        if "NetworkError" in str(type(e)) or "ConnectError" in error_message:
            logger.error("=" * 60)
            logger.error("ОШИБКА ПОДКЛЮЧЕНИЯ К TELEGRAM API")
            logger.error("=" * 60)
            logger.error("Возможные причины:")
            logger.error("1. Нет подключения к интернету")
            logger.error("2. Неверный TELEGRAM_BOT_TOKEN в .env файле")
            logger.error("3. Telegram API временно недоступен")
            logger.error("4. Проблемы с прокси/файрволом")
            logger.error("")
            logger.error("Что проверить:")
            logger.error("- Убедитесь что интернет работает")
            logger.error("- Проверьте токен бота в .env файле")
            logger.error("- Создайте нового бота через @BotFather если нужно")
            logger.error("=" * 60)
        else:
            logger.error(f"Fatal error in main: {e}", exc_info=True)

        raise
    finally:
        # Cleanup
        if _bot_instance and _llm_client and _db_manager:
            daily_summary_mgr = _bot_instance.application.bot_data.get("daily_summary_manager") if _bot_instance else None
            await cleanup_application(_bot_instance, _llm_client, _db_manager, _mcp_managers, daily_summary_mgr)


def run():
    """Run the application (synchronous wrapper)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Already handled in main()
    except Exception as e:
        logger = get_logger()
        logger.error(f"Application crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()

