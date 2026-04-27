"""
Seat Sniper (Phase 2)
Fast, lightweight seat checker using requests instead of Selenium.
Runs every 5 minutes and only checks CRNs that users are actively tracking.
"""

import re
import sys
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Course, Track, User, NotificationLog
from app.config import settings


class SeatSniper:
    """Checks seat availability for tracked courses"""

    DETAIL_URL_TEMPLATE = (
        "https://selfservice.mypurdue.purdue.edu/prod/"
        "bwckschd.p_disp_detail_sched?term_in={term_code}&crn_in={crn}"
    )

    def __init__(self, use_proxy: bool = False):
        """Initialize the sniper"""
        self.db = SessionLocal()
        self.use_proxy = use_proxy
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Setup proxy if configured
        if use_proxy and settings.PROXY_URL:
            self.session.proxies = {
                'http': settings.PROXY_URL,
                'https': settings.PROXY_URL
            }

    def check_seat_availability(self, crn: str, term_code: str) -> Optional[Dict]:
        """
        Check seat availability for a specific CRN.

        Returns:
            Dict with seat information or None if failed
        """
        url = self.DETAIL_URL_TEMPLATE.format(term_code=term_code, crn=crn)

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the Registration Availability table
            # Look for table header containing "Registration Availability"
            seat_data = self._parse_seat_info(soup)

            if seat_data:
                seat_data['last_checked'] = datetime.now()
                return seat_data

        except requests.RequestException as e:
            print(f"Error checking CRN {crn}: {str(e)}")

        return None

    def _parse_seat_info(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Parse seat information from the course detail page.

        The page has a table with header "Registration Availability"
        with columns: Capacity | Actual | Remaining
        and a row starting with "Seats" containing the values.
        """
        try:
            # Find all tables
            tables = soup.find_all('table', class_='datadisplaytable')

            for table in tables:
                # Look for "Registration Availability" header
                caption = table.find('caption', class_='captiontext')
                if caption and 'Registration Availability' in caption.get_text():
                    # Found the right table, now parse the seat row
                    rows = table.find_all('tr')

                    for row in rows:
                        # Look for the "Seats" row (not "Waitlist Seats")
                        th = row.find('th')
                        if th and th.get_text().strip() == 'Seats':
                            # Get all td cells in this row
                            cells = row.find_all('td')
                            if len(cells) >= 3:
                                remaining = int(cells[2].get_text().strip())
                                return {
                                    'seats_capacity': int(cells[0].get_text().strip()),
                                    'seats_available': int(cells[1].get_text().strip()),
                                    'seats_remaining': max(0, remaining),
                                }

        except Exception as e:
            print(f"Error parsing seat info: {str(e)}")

        return None

    def update_course_seats(self, course: Course, seat_data: Dict):
        """Update course seat information in database"""
        try:
            course.seats_capacity = seat_data['seats_capacity']
            course.seats_available = seat_data['seats_available']
            course.seats_remaining = seat_data['seats_remaining']
            course.last_checked = seat_data['last_checked']

            self.db.commit()

        except Exception as e:
            print(f"Error updating course {course.crn}: {str(e)}")
            self.db.rollback()

    def process_track_notifications(self, track: Track, old_seats: int, new_seats: int):
        """
        Process notifications for a track based on seat changes.

        Args:
            track: The Track object
            old_seats: Previous seat count
            new_seats: Current seat count
        """
        # Determine if we need to notify
        notify = False
        notification_type = None

        # Seat opened (was 0, now > 0)
        if old_seats == 0 and new_seats > 0 and track.notify_on_open:
            notify = True
            notification_type = "seat_open"
            track.last_status = "open"

        # Seat closed (was > 0, now 0)
        elif old_seats > 0 and new_seats == 0 and track.notify_on_close:
            notify = True
            notification_type = "seat_closed"
            track.last_status = "closed"

        # Update track status
        track.last_seats = new_seats
        track.last_checked = datetime.now()

        if notify:
            track.last_notified = datetime.now()
            self.send_notification(track, notification_type, new_seats)

        self.db.commit()

    def send_notification(self, track: Track, notification_type: str, seats: int):
        """
        Send notification via Email.

        Args:
            track: The Track object
            notification_type: "seat_open" or "seat_closed"
            seats: Number of seats available
        """
        # Import here to avoid circular dependency
        from .notifier import send_email_notification

        try:
            user = track.user
            course = track.course

            # Create message
            if notification_type == "seat_open":
                subject = f"🎯 SEAT OPEN! {course.course_code}"
                message = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #2e7d32; margin-top: 0;">🎯 Seat Open!</h2>
                    <p style="font-size: 16px;">Good news! A seat has opened up for <strong>{course.course_code} - {course.title}</strong>.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>CRN:</strong> {course.crn}</p>
                        <p style="margin: 5px 0;"><strong>Seats Available:</strong> {seats}</p>
                        <p style="margin: 5px 0;"><strong>Time:</strong> {course.time} {course.days}</p>
                        <p style="margin: 5px 0;"><strong>Instructor:</strong> {course.instructor}</p>
                    </div>

                    <p>Go register now before it's gone!</p>
                    
                    <a href="https://mypurdue.purdue.edu" style="display: inline-block; background-color: #cfb991; color: #000; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Go to myPurdue</a>
                </div>
                """
            else:
                subject = f"⚠️ Seat Closed: {course.course_code}"
                message = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #d32f2f; margin-top: 0;">⚠️ Seat Closed</h2>
                    <p style="font-size: 16px;">Bad news. The seat for <strong>{course.course_code} - {course.title}</strong> has been filled.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>CRN:</strong> {course.crn}</p>
                        <p style="margin: 5px 0;"><strong>Status:</strong> All seats filled</p>
                    </div>

                    <p>We'll keep watching and let you know if another one opens up.</p>
                </div>
                """

            # Send Email
            success, error = send_email_notification(user.email, subject, message)

            # Log notification
            log = NotificationLog(
                user_id=user.id,
                course_id=course.id,
                notification_type=notification_type,
                message=subject,  # Log subject instead of full HTML
                status="sent" if success else "failed",
                error_message=error
            )
            self.db.add(log)
            self.db.commit()

            if success:
                print(f"  ✓ Sent {notification_type} email for CRN {course.crn} to {user.email}")
            else:
                print(f"  ✗ Failed to send email: {error}")

        except Exception as e:
            print(f"  ✗ Error sending notification: {str(e)}")

    def run_check_cycle(self):
        """Run a complete check cycle for all tracked courses"""
        print(f"Starting Seat Sniper check cycle at {datetime.now()}")
        print("-" * 60)

        # Only check active tracks for the current listed term. Old-term tracks
        # stay in the database but do not consume worker cycles.
        active_tracks = self.db.query(Track).join(Course).filter(
            Track.is_active == True,
            Course.term_code == settings.CURRENT_TERM_CODE,
            Course.is_listed == True
        ).all()

        if not active_tracks:
            print("No active tracks found.")
            return

        # Group tracks by term-scoped CRN to avoid duplicate checks across semesters
        crn_tracks = {}
        for track in active_tracks:
            course_key = (track.course.term_code, track.course.crn)
            if course_key not in crn_tracks:
                crn_tracks[course_key] = []
            crn_tracks[course_key].append(track)

        print(f"Checking {len(crn_tracks)} unique courses for {len(active_tracks)} total tracks...")

        checked = 0
        notifications_sent = 0

        for (_, crn), tracks in crn_tracks.items():
            course = tracks[0].course  # All tracks share the same course
            old_seats = course.seats_remaining

            print(f"Checking CRN {crn} ({course.course_code})...")

            # Check seat availability
            seat_data = self.check_seat_availability(crn, course.term_code)

            if seat_data:
                new_seats = seat_data['seats_remaining']
                print(f"  Seats: {new_seats}/{seat_data['seats_capacity']} available")

                # Update course in database
                self.update_course_seats(course, seat_data)

                # Process notifications for all tracks of this course
                for track in tracks:
                    old_track_seats = track.last_seats
                    self.process_track_notifications(track, old_track_seats, new_seats)

                    # Count notifications
                    if (old_track_seats == 0 and new_seats > 0 and track.notify_on_open) or \
                       (old_track_seats > 0 and new_seats == 0 and track.notify_on_close):
                        notifications_sent += 1

                checked += 1
            else:
                print(f"  Failed to check seats")

        print("-" * 60)
        print(f"Check cycle complete!")
        print(f"  - Courses checked: {checked}/{len(crn_tracks)}")
        print(f"  - Notifications sent: {notifications_sent}")

    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def run_sniper():
    """Main function to run the seat sniper"""
    try:
        with SeatSniper(use_proxy=False) as sniper:
            sniper.run_check_cycle()

    except Exception as e:
        print(f"Error running seat sniper: {str(e)}")
        raise


if __name__ == "__main__":
    run_sniper()
