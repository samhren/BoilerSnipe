"""
Telegram notification service
"""

from typing import Tuple, Optional
import requests
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings


def send_telegram_notification(chat_id: str, message: str) -> Tuple[bool, Optional[str]]:
    """
    Send notification via Telegram Bot API.

    Args:
        chat_id: Telegram chat ID of the recipient
        message: Message text to send

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        print("⚠️  Telegram not configured. Set TELEGRAM_BOT_TOKEN in .env")
        return False, "Telegram bot token not configured"

    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)

        data = response.json()

        if data.get("ok"):
            return True, None
        else:
            error_msg = data.get("description", "Unknown error")
            print(f"  ✗ Telegram error: {error_msg}")
            return False, error_msg

    except requests.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        print(f"  ✗ {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"  ✗ {error_msg}")
        return False, error_msg


def test_notification(chat_id: str):
    """
    Test the notification system by sending a test message.

    Args:
        chat_id: Telegram chat ID to send test to
    """
    message = "🎯 Test notification from BoilerSnipe! If you receive this, notifications are working."

    print(f"Sending test notification to chat ID {chat_id}...")
    success, error = send_telegram_notification(chat_id, message)

    if success:
        print("✓ Test notification sent successfully!")
    else:
        print(f"✗ Failed to send test notification: {error}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_chat_id = sys.argv[1]
        test_notification(test_chat_id)
    else:
        print("Usage: python notifier.py <telegram_chat_id>")
        print("\nTo get your chat ID:")
        print("1. Create a bot via @BotFather on Telegram")
        print("2. Start a chat with your bot")
        print("3. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
        print("4. Look for 'chat': {'id': YOUR_CHAT_ID}")
