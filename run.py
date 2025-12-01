#!/usr/bin/env python3
"""Simple script to run Rick Sanchez Bot."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def print_banner():
    """Print startup banner."""
    banner = r"""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   🧪 Rick Sanchez Telegram Bot 🧪                    ║
    ║                                                       ║
    ║   *burp* Wubba Lubba Dub Dub!                       ║
    ║                                                       ║
    ║   Version: 1.0.0                                     ║
    ║   Powered by: Yandex Cloud LLM                       ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)
    print("\n🚀 Starting bot...\n")


def main():
    """Main entry point."""
    try:
        print_banner()
        
        # Import and run
        from src.main import run
        run()
        
    except ImportError as e:
        print(f"\n❌ Error: Failed to import required modules: {e}")
        print("\n💡 Make sure you have installed all dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ Error: Required file not found: {e}")
        print("\n💡 Make sure you have:")
        print("   1. Created .env file with required variables")
        print("   2. Set TELEGRAM_BOT_TOKEN and YANDEX_API_KEY")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user (Ctrl+C)")
        print("*urp* See you later, Morty!\n")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

