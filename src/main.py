"""Main application entry point."""

import asyncio
import signal

from .config import get_settings, setup_logger, get_logger
from .llm import YandexLLMClient, ResponseProcessor
from .bot import RickBot, StateManager
from .bot.llm_integration import LLMIntegration

# Global references for cleanup
_bot_instance = None
_llm_client = None


async def initialize_application():
    """Initialize all application components.
    
    Returns:
        Tuple of (bot, llm_client) instances
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
        api_key=settings.yandex_api_key,
        folder_id=settings.yandex_folder_id,
        model_name=settings.yandex_model_name,
        model_uri=settings.yandex_model_uri,
        endpoint=settings.yandex_llm_endpoint,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        ssl_verify=settings.ssl_verify
    )
    logger.info("✓ LLM client initialized")
    
    # Initialize response processor
    response_processor = ResponseProcessor()
    
    # Initialize state manager
    logger.info("Initializing state manager...")
    state_manager = StateManager(
        cleanup_hours=settings.user_state_cleanup_hours
    )
    logger.info("✓ State manager initialized")
    
    # Initialize LLM integration
    logger.info("Initializing LLM integration...")
    llm_integration = LLMIntegration(
        llm_client=llm_client,
        state_manager=state_manager,
        response_processor=response_processor
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
    
    logger.info("=" * 60)
    logger.info("Initialization complete!")
    logger.info("=" * 60)
    
    return bot, llm_client


async def cleanup_application(bot: RickBot, llm_client: YandexLLMClient):
    """Cleanup application resources.
    
    Args:
        bot: Rick bot instance
        llm_client: LLM client instance
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
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    logger.info("=" * 60)
    logger.info("Cleanup complete. Goodbye!")
    logger.info("=" * 60)


async def main():
    """Main application entry point."""
    global _bot_instance, _llm_client
    
    logger = get_logger()
    
    try:
        # Initialize
        bot, llm_client = await initialize_application()
        _bot_instance = bot
        _llm_client = llm_client
        
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
        if _bot_instance and _llm_client:
            await cleanup_application(_bot_instance, _llm_client)


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

