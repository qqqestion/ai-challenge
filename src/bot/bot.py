"""Main Telegram bot implementation."""

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)
from ..config import get_logger, Settings
from .state_manager import StateManager
from .handlers import (
    start_command,
    help_command,
    plan_vacation_command,
    mode_rick_command,
    mode_morty_command,
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
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )
        
        # Store dependencies in bot_data for handlers
        self.application.bot_data["state_manager"] = state_manager
        self.application.bot_data["llm_integration"] = llm_integration
        self.application.bot_data["max_message_length"] = settings.max_message_length
        
        # Register handlers
        self._register_handlers()
        
        # Set bot commands menu
        self._set_bot_commands()
        
        logger.info("RickBot initialized successfully")
    
    def _register_handlers(self):
        """Register all command and message handlers."""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("plan_vacation", plan_vacation_command))
        app.add_handler(CommandHandler("mode_rick", mode_rick_command))
        app.add_handler(CommandHandler("mode_morty", mode_morty_command))
        
        # Message handler (for non-command messages)
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_message
            )
        )
        
        # Error handler
        app.add_error_handler(error_handler)
        
        logger.info("All handlers registered")
    
    def _set_bot_commands(self):
        """Set bot commands menu for Telegram UI."""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("help", "Справка по командам"),
            BotCommand("plan_vacation", "Спланировать отпуск"),
            BotCommand("mode_rick", "Переключиться на режим Рика"),
            BotCommand("mode_morty", "Переключиться на режим Морти"),
        ]
        
        # Set commands asynchronously after bot is initialized
        # This will be called in start() method after initialization
        self._bot_commands = commands
        logger.info("Bot commands menu configured")
    
    async def start(self):
        """Start the bot."""
        logger.info("Starting Rick Bot...")
        
        # Initialize and start application first
        await self.application.initialize()
        await self.application.start()
        
        # Set bot commands menu
        try:
            await self.application.bot.set_my_commands(self._bot_commands)
            logger.info("Bot commands menu set successfully")
        except Exception as e:
            logger.warning(f"Could not set bot commands: {e}")
        
        # Now we can get bot info
        try:
            bot_info = await self.application.bot.get_me()
            logger.info(f"Bot username: @{bot_info.username}")
            logger.info(f"Bot name: {bot_info.first_name}")
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

