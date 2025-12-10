"""Main Telegram bot implementation."""

from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from ..config import get_logger, Settings
from .state_manager import StateManager
from .handlers import (
    start_command,
    help_command,
    reset_command,
    temperature_command,
    commands_command,
    change_model_command,
    change_model_callback,
    handle_message,
    error_handler
)

logger = get_logger(__name__)


class RickBot:
    """Rick Sanchez Telegram Bot."""
    
    def __init__(
        self,
        settings: Settings,
        state_manager: StateManager,
        llm_integration
    ):
        """Initialize Rick Bot.
        
        Args:
            settings: Application settings
            state_manager: User state manager
            llm_integration: LLM integration handler
        """
        self.settings = settings
        self.state_manager = state_manager
        self.llm_integration = llm_integration
        
        # Create application
        request = HTTPXRequest(httpx_kwargs={"verify": settings.telegram_ssl_verify})
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .request(request)
            .build()
        )
        
        # Store dependencies in bot_data for handlers
        self.application.bot_data["state_manager"] = state_manager
        self.application.bot_data["llm_integration"] = llm_integration
        self.application.bot_data["max_message_length"] = settings.max_message_length
        
        # Register handlers
        self._register_handlers()
        
        logger.info("RickBot initialized successfully")
    
    def _register_handlers(self):
        """Register all command and message handlers."""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("commands", commands_command))
        app.add_handler(CommandHandler("reset", reset_command))
        app.add_handler(CommandHandler("temperature", temperature_command))
        app.add_handler(CommandHandler("change_model", change_model_command))
        
        # Message handler (for non-command messages)
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_message
            )
        )

        # Callback query handler for model selection
        app.add_handler(CallbackQueryHandler(change_model_callback, pattern="^change_model:"))
        
        # Error handler
        app.add_error_handler(error_handler)
        
        logger.info("All handlers registered")
    
    async def _set_bot_commands(self):
        """Set bot commands menu for Telegram."""
        from telegram import BotCommand
        
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("help", "Подробная справка"),
            BotCommand("commands", "Список всех команд"),
            BotCommand("temperature", "Настройка температуры"),
            BotCommand("change_model", "Выбрать модель"),
            BotCommand("reset", "Очистить историю"),
        ]
        
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands menu set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot commands menu: {e}")
    
    async def start(self):
        """Start the bot."""
        logger.info("Starting Rick Bot...")
        
        # Initialize and start application first
        await self.application.initialize()
        await self.application.start()
        
        # Now we can get bot info
        try:
            bot_info = await self.application.bot.get_me()
            logger.info(f"Bot username: @{bot_info.username}")
            logger.info(f"Bot name: {bot_info.first_name}")
            
            # Set bot commands menu
            await self._set_bot_commands()
        except Exception as e:
            logger.warning(f"Could not get bot info: {e}")
            logger.info("Bot will continue running...")
        
        # Start polling
        await self.application.updater.start_polling(
            allowed_updates=["message", "callback_query"]
        )
        
        logger.info("Bot is running! Press Ctrl+C to stop.")
    
    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping Rick Bot...")
        
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        logger.info("Bot stopped successfully")
    
    def run(self):
        """Run the bot (blocking call)."""
        logger.info("Running Rick Bot in polling mode...")
        self.application.run_polling(
            allowed_updates=["message", "callback_query"]
        )

