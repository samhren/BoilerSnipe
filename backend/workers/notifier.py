"""
Email notification service using Resend
"""

import os
import sys
import time
import threading
from html import escape
from collections import deque
from typing import Tuple, Optional
from pathlib import Path
import resend


class RateLimiter:
    """Simple rate limiter using a sliding window approach."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: deque = deque()
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Block until we're under the rate limit."""
        with self.lock:
            now = time.time()

            # Remove timestamps outside the window
            while self.timestamps and self.timestamps[0] < now - self.window_seconds:
                self.timestamps.popleft()

            # If we're at the limit, wait until the oldest request falls outside the window
            if len(self.timestamps) >= self.max_requests:
                sleep_time = self.timestamps[0] - (now - self.window_seconds)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # Clean up again after sleeping
                    now = time.time()
                    while self.timestamps and self.timestamps[0] < now - self.window_seconds:
                        self.timestamps.popleft()

            # Record this request
            self.timestamps.append(time.time())


# Global rate limiter for email sending (10 emails per second max)
_email_rate_limiter = RateLimiter(max_requests=10, window_seconds=1.0)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings


def _email_shell(content: str, preheader: str = "") -> str:
    """Wrap notification content in the shared BoilerSnipe email design."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>@media(max-width:600px){{.bs-card{{width:100%!important}}.bs-pad{{padding-left:20px!important;padding-right:20px!important}}.bs-stack{{display:block!important;width:100%!important}}}}</style>
</head><body style="margin:0;background:#F6F2E9;color:#24221E;-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F6F2E9"><tr><td align="center" style="padding:32px 16px">
<table role="presentation" class="bs-card" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background:#FFFEFA;border:1px solid #DDD7CA;border-radius:12px;overflow:hidden">
<tr><td class="bs-pad" style="padding:22px 40px;border-bottom:1px solid #DDD7CA;font:700 15px Arial,sans-serif">◎&nbsp;&nbsp;BoilerSnipe</td></tr>
{content}
<tr><td class="bs-pad" style="padding:22px 40px;background:#F6F2E9;border-top:1px solid #DDD7CA;font:12px/1.6 Arial,sans-serif;color:#716C62">BoilerSnipe · Free, independent, and not affiliated with Purdue University.<br><a href="https://boilersnipe.com/dashboard" style="color:#8E6F3E">Manage alerts</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="https://boilersnipe.com/privacy" style="color:#8E6F3E">Privacy</a></td></tr>
</table></td></tr></table></body></html>"""


def build_course_notification_email(course, notification_type: str, seats: int) -> Tuple[str, str]:
    """Build a seat-opened or section-closed email using shared design tokens."""
    code = escape(str(course.course_code or "Course"))
    title = escape(str(course.title or "Untitled course"))
    crn = escape(str(course.crn or "—"))
    section = escape(str(course.section or "—"))
    schedule_type = escape(str(course.schedule_type or "Section"))
    meeting = escape(f"{course.days or 'TBA'} · {course.time or 'TBA'}")
    instructor = escape(str(course.instructor or "TBA"))
    term = escape(str(course.term_name or course.term_code or "Current term"))

    is_open = notification_type == "seat_open"
    subject = f"{code} (CRN {crn}) has {seats} {'seat' if seats == 1 else 'seats'} open" if is_open else f"{code} (CRN {crn}) is now full"
    label = "Seat available" if is_open else "Section full"
    headline = "A seat just opened." if is_open else "This section just filled up."
    status_color = "#2E6B4F" if is_open else "#716C62"
    status_bg = "#EAF2ED" if is_open else "#F1EEE6"
    summary = (
        f"{code} (CRN {crn}) now has {seats} {'seat' if seats == 1 else 'seats'} available. Register through Purdue before it fills again."
        if is_open else
        f"{code} (CRN {crn}) reached 0 open seats. We’ll keep checking and email you when a seat reopens."
    )
    cta_href = "https://selfservice.mypurdue.purdue.edu/" if is_open else "https://boilersnipe.com/dashboard"
    cta_text = "Register on Purdue →" if is_open else "Open my watchlist →"
    seat_text = f"{seats} available" if is_open else "0 available"

    content = f"""
<tr><td class="bs-pad" style="padding:28px 40px 0"><div style="padding:14px 18px;background:{status_bg};border-left:3px solid {status_color};border-radius:0 8px 8px 0;font:700 13px Arial,sans-serif;color:{status_color};text-transform:uppercase;letter-spacing:.02em">{label}</div></td></tr>
<tr><td class="bs-pad" style="padding:22px 40px 0"><h1 style="margin:0;font:26px/1.3 Georgia,serif;color:#24221E">{headline}</h1><p style="margin:10px 0 0;font:15px/1.6 Arial,sans-serif;color:#716C62">{summary}</p></td></tr>
<tr><td class="bs-pad" style="padding:24px 40px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #DDD7CA;border-radius:10px"><tr><td style="padding:20px 22px">
<div style="font:700 17px Arial,sans-serif;color:#24221E">{code} · {title}</div><div style="padding-top:5px;font:13px 'Courier New',monospace;color:#716C62">CRN {crn} · Section {section} · {schedule_type}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;border-top:1px solid #DDD7CA"><tr>
<td class="bs-stack" width="50%" style="padding-top:14px;font:11px/1.7 Arial,sans-serif;color:#716C62;text-transform:uppercase">Meets<br><span style="font:14px 'Courier New',monospace;color:#24221E;text-transform:none">{meeting}</span></td>
<td class="bs-stack" width="50%" style="padding-top:14px;font:11px/1.7 Arial,sans-serif;color:#716C62;text-transform:uppercase">Instructor<br><span style="font:14px Arial,sans-serif;color:#24221E;text-transform:none">{instructor}</span></td></tr><tr>
<td class="bs-stack" width="50%" style="padding-top:14px;font:11px/1.7 Arial,sans-serif;color:#716C62;text-transform:uppercase">Seats<br><span style="font:700 14px 'Courier New',monospace;color:{status_color};text-transform:none">{seat_text}</span></td>
<td class="bs-stack" width="50%" style="padding-top:14px;font:11px/1.7 Arial,sans-serif;color:#716C62;text-transform:uppercase">Term<br><span style="font:14px Arial,sans-serif;color:#24221E;text-transform:none">{term}</span></td>
</tr></table></td></tr></table></td></tr>
<tr><td class="bs-pad" style="padding:28px 40px 8px"><a href="{cta_href}" style="display:inline-block;padding:14px 24px;background:#24221E;border-radius:8px;font:700 15px Arial,sans-serif;color:#FFFEFA;text-decoration:none">{cta_text}</a></td></tr>
<tr><td class="bs-pad" style="padding:10px 40px 30px;font:12.5px/1.6 Arial,sans-serif;color:#9A9486">BoilerSnipe checks this section every 5 minutes and never registers automatically.</td></tr>"""
    return subject, _email_shell(content, summary)


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

    # Rate limit: wait if we've sent too many emails recently
    _email_rate_limiter.wait_if_needed()

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
    subject = "Test notification from BoilerSnipe"
    html_content = _email_shell('<tr><td class="bs-pad" style="padding:36px 40px"><h1 style="margin:0;font:26px Georgia,serif">Notifications are working.</h1><p style="font:15px/1.6 Arial,sans-serif;color:#716C62">This test email reached your inbox successfully.</p></td></tr>', "Your BoilerSnipe test notification was delivered.")

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
    subject = "Welcome to BoilerSnipe"
    html_content = _email_shell('''<tr><td class="bs-pad" style="padding:36px 40px"><p style="margin:0 0 8px;font:12px 'Courier New',monospace;color:#8E6F3E;text-transform:uppercase;letter-spacing:.08em">Your watchlist is ready</p><h1 style="margin:0;font:26px/1.3 Georgia,serif">Welcome to BoilerSnipe.</h1><p style="font:15px/1.7 Arial,sans-serif;color:#716C62">Search for the exact section you need, watch its CRN, and we’ll email you when availability changes.</p><a href="https://boilersnipe.com/search" style="display:inline-block;margin-top:10px;padding:14px 24px;background:#24221E;border-radius:8px;font:700 15px Arial,sans-serif;color:#FFFEFA;text-decoration:none">Find a section →</a><p style="margin-top:24px;font:12.5px/1.6 Arial,sans-serif;color:#9A9486">No Purdue login is required. BoilerSnipe never registers or holds a seat for you.</p></td></tr>''', "Welcome to BoilerSnipe. Your watchlist is ready.")
    print(f"Sending welcome email to {to_email}...")
    send_email_notification(to_email, subject, html_content)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_email = sys.argv[1]
        test_notification(test_email)
    else:
        print("Usage: python notifier.py <email_address>")
