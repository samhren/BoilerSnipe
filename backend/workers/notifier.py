"""
Email notification service using Resend
"""

import os
import sys
from typing import Tuple, Optional
from pathlib import Path
import resend

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings


def send_email_notification(to_email: str, subject: str, html_content: str) -> Tuple[bool, Optional[str]]:
    """
    Send notification via Resend API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if not settings.RESEND_API_KEY:
        print("⚠️  Resend not configured. Set RESEND_API_KEY in .env")
        return False, "Resend API key not configured"

    resend.api_key = settings.RESEND_API_KEY

    try:
        params = {
            "from": "BoilerSnipe <notifications@boilersnipe.com>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        email = resend.Emails.send(params)
        
        # Resend returns an object with 'id' on success
        if email and email.get("id"):
            return True, None
        else:
            return False, "Failed to send email (unknown error)"

    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        print(f"  ✗ {error_msg}")
        return False, error_msg


def test_notification(to_email: str):
    """
    Test the notification system by sending a test email.

    Args:
        to_email: Email address to send test to
    """
    subject = "🎯 Test Notification from BoilerSnipe"
    html_content = """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Test Notification</h2>
        <p>If you received this email, BoilerSnipe notifications are working correctly!</p>
        <p>Happy hunting,</p>
        <p>The BoilerSnipe Team</p>
    </div>
    """

    print(f"Sending test email to {to_email}...")
    success, error = send_email_notification(to_email, subject, html_content)

    if success:
        print("✓ Test notification sent successfully!")
    else:
        print(f"✗ Failed to send test notification: {error}")


def send_welcome_email(to_email: str):
    """
    Send a welcome email to a new user.
    """
    subject = "Welcome to BoilerSnipe! 🚂"
    html_content = """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.6;">
        <h2 style="color: #CFB991; background-color: #000000; padding: 10px; border-radius: 5px;">Welcome to BoilerSnipe!</h2>
        <p>Hey there! 👋</p>
        <p>Thanks for creating an account. You're now ready to snipe those elusive open seats.</p>
        
        <h3>How it works:</h3>
        <ol>
            <li><b>Search</b> for the course you want to get into.</li>
            <li><b>Track</b> the course by clicking the bell icon.</li>
            <li><b>Wait</b> - we'll send you an email the moment a seat opens up!</li>
        </ol>
        
        <p>Happy hunting,</p>
        <p>The BoilerSnipe Team</p>
        <p style="font-size: 12px; color: #888;">P.S. Make sure to check your spam folder and mark us as safe so you don't miss an alert.</p>
    </div>
    """
    print(f"Sending welcome email to {to_email}...")
    send_email_notification(to_email, subject, html_content)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_email = sys.argv[1]
        test_notification(test_email)
    else:
        print("Usage: python notifier.py <email_address>")
