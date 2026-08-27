"""
Seat Sniper (Phase 2)
Fast, lightweight seat checker using requests instead of Selenium.
Runs every 5 minutes and only checks CRNs that users are actively tracking.

Rate-limit resilience
---------------------
Purdue throttles by IP and signals it with an HTTP 200 whose body is a short
"too many requests" notice rather than a status code. That page parses as "no
seat table found", which is indistinguishable from a parse bug unless we look
for it explicitly. Everything below exists to make a throttle loud, to stop
hammering the wall once we hit it, and to remember that we hit it after this
process builds its next SeatSniper.
"""

import logging
import random
import sys
import threading
import time
import requests
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Course, Track, User, NotificationLog
from app.config import settings


logger = logging.getLogger(__name__)


class CheckStatus(str, Enum):
    """Outcome of a single seat check.

    These are deliberately distinct: a PARSE_FAILED on a genuine course page is
    a bug in our parser, while BLOCKED means Purdue is throttling us. Collapsing
    both into `None` is what made the 2026-08-25 outage silent for 24 hours.
    """

    OK = "ok"
    BLOCKED = "blocked"
    NETWORK_ERROR = "network_error"
    PARSE_FAILED = "parse_failed"


@dataclass
class SeatCheckResult:
    """Result of one `check_seat_availability` call."""

    status: CheckStatus
    data: Optional[Dict] = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status is CheckStatus.OK

    @property
    def is_rate_limit_signal(self) -> bool:
        """Whether this outcome should count toward tripping the breaker.

        Read timeouts and dropped connections are how Purdue's throttle
        manifests once it stops answering politely, so they count too.
        """
        return self.status in (CheckStatus.BLOCKED, CheckStatus.NETWORK_ERROR)


@dataclass
class CycleSummary:
    """What a single `run_check_cycle()` actually did.

    Returned so the scheduler (and tests) can inspect a cycle without scraping
    log lines.
    """

    total_courses: int = 0
    attempted: int = 0
    checked: int = 0
    notifications_sent: int = 0
    skipped_for_budget: int = 0
    unchecked_after_abort: int = 0
    breaker_tripped: bool = False
    skipped_for_backoff: bool = False
    status_counts: Dict[CheckStatus, int] = field(default_factory=dict)

    def record(self, status: CheckStatus) -> None:
        self.status_counts[status] = self.status_counts.get(status, 0) + 1

    @property
    def dominant_failure(self) -> Optional[CheckStatus]:
        """The most common non-OK outcome, for the summary line."""
        failures = {s: n for s, n in self.status_counts.items() if s is not CheckStatus.OK}
        if not failures:
            return None
        return max(failures.items(), key=lambda kv: kv[1])[0]


# --- Block-page detection -------------------------------------------------
#
# The observed block page is ~519 bytes and reads:
#   "We are sorry, but the site has received too many requests. Please try
#    again later."
# A real course detail page is ~12-13 KB, so a generous length ceiling keeps
# this from ever misfiring on a legitimate page that happens to contain the
# phrase.
BLOCK_PAGE_MARKERS = (
    "too many requests",
    "received too many requests",
)
BLOCK_PAGE_MAX_BYTES = 4096
BLOCKED_STATUS_CODES = (429, 503)

# --- Cross-process-lifetime backoff --------------------------------------
#
# `run_sniper()` builds a fresh SeatSniper every cycle, so per-instance state
# resets and buys nothing. The scheduler process is long-lived, so backoff and
# rotation live at module scope where they actually survive between cycles.
BACKOFF_BASE_MINUTES = 5.0
BACKOFF_JITTER = 0.2  # +/- 20%


class _SniperRuntimeState:
    """Backoff and rotation state shared by every SeatSniper in this process."""

    def __init__(self):
        self._lock = threading.Lock()
        self.backoff_until: Optional[datetime] = None
        self.backoff_level: int = 0
        self.rotation_offset: int = 0
        self.last_success_at: Optional[datetime] = None

    def backoff_remaining_seconds(self, now: Optional[datetime] = None) -> float:
        """Seconds left on an active backoff, or 0.0 if none is in force."""
        now = now or datetime.now()
        with self._lock:
            if self.backoff_until is None:
                return 0.0
            remaining = (self.backoff_until - now).total_seconds()
            if remaining <= 0:
                self.backoff_until = None
                return 0.0
            return remaining

    def trip_backoff(self, now: Optional[datetime] = None) -> float:
        """Escalate backoff one level. Returns the delay applied, in minutes."""
        now = now or datetime.now()
        with self._lock:
            self.backoff_level += 1
            raw = BACKOFF_BASE_MINUTES * (2 ** (self.backoff_level - 1))
            capped = min(raw, settings.SNIPER_BACKOFF_MAX_MINUTES)
            jittered = capped * random.uniform(1 - BACKOFF_JITTER, 1 + BACKOFF_JITTER)
            jittered = max(0.0, min(jittered, settings.SNIPER_BACKOFF_MAX_MINUTES))
            self.backoff_until = now + timedelta(minutes=jittered)
            return jittered

    def record_success(self, now: Optional[datetime] = None) -> bool:
        """Clear backoff after a successful check. Returns True if it cleared one."""
        now = now or datetime.now()
        with self._lock:
            was_backing_off = self.backoff_level > 0 or self.backoff_until is not None
            self.backoff_level = 0
            self.backoff_until = None
            self.last_success_at = now
            return was_backing_off

    def advance_rotation(self, by: int, total: int) -> None:
        """Move the cycle start point so the same tail is not starved forever."""
        with self._lock:
            if total > 0:
                self.rotation_offset = (self.rotation_offset + by) % total

    def current_rotation(self, total: int) -> int:
        with self._lock:
            return self.rotation_offset % total if total > 0 else 0

    def reset(self) -> None:
        """Test hook - drop all state."""
        with self._lock:
            self.backoff_until = None
            self.backoff_level = 0
            self.rotation_offset = 0
            self.last_success_at = None


runtime_state = _SniperRuntimeState()


def looks_like_block_page(body: str) -> bool:
    """Whether a 200 response body is really Purdue's rate-limit notice."""
    if not body:
        return False
    if len(body.encode("utf-8", errors="ignore")) > BLOCK_PAGE_MAX_BYTES:
        return False
    lowered = body.lower()
    return any(marker in lowered for marker in BLOCK_PAGE_MARKERS)


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
            'User-Agent': settings.USER_AGENT
        })

        # Setup proxy if configured
        if use_proxy and settings.PROXY_URL:
            self.session.proxies = {
                'http': settings.PROXY_URL,
                'https': settings.PROXY_URL
            }

    def check_seat_availability(self, crn: str, term_code: str) -> SeatCheckResult:
        """
        Check seat availability for a specific CRN.

        Returns:
            SeatCheckResult whose status distinguishes a successful read from a
            throttle, a network failure, and a page we could not parse.
        """
        url = self.DETAIL_URL_TEMPLATE.format(term_code=term_code, crn=crn)

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code in BLOCKED_STATUS_CODES:
                return SeatCheckResult(
                    CheckStatus.BLOCKED,
                    detail=f"HTTP {response.status_code} from Purdue",
                )

            response.raise_for_status()

            # Purdue serves its rate-limit notice as a 200, so raise_for_status
            # above will never catch it. Sniff the body before parsing.
            if looks_like_block_page(response.text):
                return SeatCheckResult(
                    CheckStatus.BLOCKED,
                    detail="HTTP 200 rate-limit notice page",
                )

            soup = BeautifulSoup(response.text, 'html.parser')
            seat_data = self._parse_seat_info(soup)

            if seat_data:
                seat_data['last_checked'] = datetime.now()
                return SeatCheckResult(CheckStatus.OK, data=seat_data)

            return SeatCheckResult(
                CheckStatus.PARSE_FAILED,
                detail="no Registration Availability table on a non-block page",
            )

        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code in BLOCKED_STATUS_CODES:
                return SeatCheckResult(
                    CheckStatus.BLOCKED, detail=f"HTTP {status_code} from Purdue"
                )
            return SeatCheckResult(CheckStatus.NETWORK_ERROR, detail=str(e))

        except requests.RequestException as e:
            # Read timeouts and RemoteDisconnected land here. During the
            # 2026-08-25 incident these ran in the hundreds per cycle - they are
            # the throttle escalating, not unrelated flakiness.
            return SeatCheckResult(CheckStatus.NETWORK_ERROR, detail=str(e))

    def _parse_seat_info(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Parse seat information from the course detail page.

        The page has a table with header "Registration Availability"
        with columns: Capacity | Actual | Remaining. Cross-listed courses can
        also include a "Cross List Seats" row, which is the aggregate cap across
        linked CRNs. The effective availability is the most restrictive row.
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
                    seats_data = None
                    cross_list_data = None

                    for row in rows:
                        th = row.find('th')
                        if not th:
                            continue

                        label = " ".join(th.get_text().split())
                        if label not in ('Seats', 'Cross List Seats'):
                            continue

                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue

                        row_data = {
                            'seats_capacity': int(cells[0].get_text().strip()),
                            'seats_available': int(cells[1].get_text().strip()),
                            'seats_remaining': max(0, int(cells[2].get_text().strip())),
                        }

                        if label == 'Seats':
                            seats_data = row_data
                        elif label == 'Cross List Seats':
                            cross_list_data = row_data

                    if seats_data and cross_list_data:
                        if cross_list_data['seats_remaining'] < seats_data['seats_remaining']:
                            return cross_list_data
                        return seats_data

                    if seats_data:
                        return seats_data

        except Exception as e:
            logger.exception("Error parsing seat info: %s", e)

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
            logger.error("Error updating course %s: %s", course.crn, e)
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
                logger.info(
                    "Sent %s email for CRN %s to %s",
                    notification_type, course.crn, user.email,
                )
            else:
                logger.error("Failed to send email: %s", error)

        except Exception as e:
            logger.exception("Error sending notification: %s", e)

    def _ordered_course_keys(self, crn_tracks: Dict) -> List[Tuple[str, str]]:
        """Course keys in a stable order, rotated to last cycle's stopping point.

        Sorting first makes the rotation meaningful: without a deterministic
        base order, "start where we left off" is not well defined.
        """
        keys = sorted(crn_tracks.keys())
        if not keys:
            return keys
        offset = runtime_state.current_rotation(len(keys))
        return keys[offset:] + keys[:offset]

    def run_check_cycle(self) -> CycleSummary:
        """Run a check cycle for tracked courses, respecting backoff and budget."""
        summary = CycleSummary()

        logger.info("Starting Seat Sniper check cycle at %s", datetime.now())

        # A tripped breaker in an earlier cycle suppresses this one entirely.
        # Grinding requests into an active block is what kept the block open.
        backoff_remaining = runtime_state.backoff_remaining_seconds()
        if backoff_remaining > 0:
            summary.skipped_for_backoff = True
            logger.warning(
                "Sniper backoff active (level %d): skipping this cycle, "
                "%.1f minutes remaining before we retry Purdue.",
                runtime_state.backoff_level, backoff_remaining / 60.0,
            )
            return summary

        # Only check active tracks for the current listed term. Old-term tracks
        # stay in the database but do not consume worker cycles.
        active_tracks = self.db.query(Track).join(Course).filter(
            Track.is_active == True,
            Course.term_code == settings.CURRENT_TERM_CODE,
            Course.is_listed == True
        ).all()

        if not active_tracks:
            logger.info("No active tracks found.")
            return summary

        # Group tracks by term-scoped CRN to avoid duplicate checks across semesters
        crn_tracks = {}
        for track in active_tracks:
            course_key = (track.course.term_code, track.course.crn)
            if course_key not in crn_tracks:
                crn_tracks[course_key] = []
            crn_tracks[course_key].append(track)

        summary.total_courses = len(crn_tracks)
        ordered_keys = self._ordered_course_keys(crn_tracks)

        # A growing course list must not silently push a cycle past the
        # scheduler interval; trim to the budget and say what got dropped.
        budget = max(1, settings.SNIPER_MAX_REQUESTS_PER_CYCLE)
        keys_to_check = ordered_keys[:budget]
        summary.skipped_for_budget = len(ordered_keys) - len(keys_to_check)

        logger.info(
            "Checking %d of %d unique courses for %d total tracks "
            "(delay %.2fs, budget %d).",
            len(keys_to_check), summary.total_courses, len(active_tracks),
            settings.SNIPER_REQUEST_DELAY_SECONDS, budget,
        )
        if summary.skipped_for_budget:
            logger.warning(
                "Per-cycle request budget of %d reached: %d course(s) skipped "
                "this cycle and will be checked first next cycle.",
                budget, summary.skipped_for_budget,
            )

        consecutive_failures = 0
        max_failures = max(1, settings.SNIPER_MAX_CONSECUTIVE_FAILURES)

        for index, course_key in enumerate(keys_to_check):
            tracks = crn_tracks[course_key]
            _, crn = course_key
            course = tracks[0].course  # All tracks share the same course

            # Pace ourselves. The incident cycle issued ~469 back-to-back
            # requests at roughly 3 req/s sustained, 24/7, from one IP.
            if index > 0 and settings.SNIPER_REQUEST_DELAY_SECONDS > 0:
                time.sleep(settings.SNIPER_REQUEST_DELAY_SECONDS)

            summary.attempted += 1
            result = self.check_seat_availability(crn, course.term_code)
            summary.record(result.status)

            if result.ok:
                if runtime_state.record_success():
                    logger.info("Sniper backoff cleared after a successful check.")
                consecutive_failures = 0

                seat_data = result.data
                new_seats = seat_data['seats_remaining']
                logger.info(
                    "CRN %s (%s): %d/%d seats available",
                    crn, course.course_code, new_seats, seat_data['seats_capacity'],
                )

                self.update_course_seats(course, seat_data)

                for track in tracks:
                    old_track_seats = track.last_seats
                    self.process_track_notifications(track, old_track_seats, new_seats)

                    if (old_track_seats == 0 and new_seats > 0 and track.notify_on_open) or \
                       (old_track_seats > 0 and new_seats == 0 and track.notify_on_close):
                        summary.notifications_sent += 1

                summary.checked += 1
                continue

            # Every failure is now logged with its own reason. A PARSE_FAILED
            # here means a real course page we could not read - a parser bug,
            # not a throttle - and must stay visibly different from BLOCKED.
            if result.status is CheckStatus.BLOCKED:
                logger.error(
                    "CRN %s (%s): BLOCKED by Purdue rate limiting - %s",
                    crn, course.course_code, result.detail,
                )
            elif result.status is CheckStatus.NETWORK_ERROR:
                logger.warning(
                    "CRN %s (%s): network error - %s",
                    crn, course.course_code, result.detail,
                )
            else:
                logger.error(
                    "CRN %s (%s): PARSE FAILED on an apparently valid page - %s",
                    crn, course.course_code, result.detail,
                )

            if result.is_rate_limit_signal:
                consecutive_failures += 1
            else:
                consecutive_failures = 0

            if consecutive_failures >= max_failures:
                summary.breaker_tripped = True
                summary.unchecked_after_abort = len(keys_to_check) - (index + 1)
                delay_minutes = runtime_state.trip_backoff()
                logger.error(
                    "CIRCUIT BREAKER TRIPPED: %d consecutive blocked/network "
                    "failures. Aborting cycle with %d course(s) unchecked. "
                    "Backing off for %.1f minutes (level %d) before the next "
                    "cycle contacts Purdue.",
                    consecutive_failures, summary.unchecked_after_abort,
                    delay_minutes, runtime_state.backoff_level,
                )
                break

        # Move the starting point forward by what we actually attempted, so a
        # budget-trimmed or aborted cycle does not starve the same tail forever.
        if summary.skipped_for_budget or summary.breaker_tripped:
            runtime_state.advance_rotation(summary.attempted, summary.total_courses)

        self._log_summary(summary)
        return summary

    def _log_summary(self, summary: CycleSummary) -> None:
        """Emit the end-of-cycle summary, loudly when the cycle was abnormal."""
        detail = (
            f"checked {summary.checked}/{summary.total_courses}, "
            f"notifications sent {summary.notifications_sent}"
        )
        if summary.skipped_for_budget:
            detail += f", {summary.skipped_for_budget} skipped for budget"
        if summary.unchecked_after_abort:
            detail += f", {summary.unchecked_after_abort} unchecked after abort"

        # The failure mode that hid the outage: checked == 0 with courses to
        # check looked exactly like a normal cycle in the logs. It never will
        # again.
        if summary.total_courses > 0 and summary.checked == 0:
            dominant = summary.dominant_failure
            reason = dominant.value if dominant else "no checks attempted"
            logger.critical(
                "SNIPER NOT FUNCTIONING: 0 of %d tracked courses were checked "
                "successfully this cycle. Dominant failure: %s. No seat-open "
                "notifications can be sent while this persists. (%s)",
                summary.total_courses, reason, detail,
            )
            return

        failures = summary.attempted - summary.checked
        if failures:
            logger.warning("Check cycle complete with %d failure(s): %s", failures, detail)
        else:
            logger.info("Check cycle complete: %s", detail)

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
            return sniper.run_check_cycle()

    except Exception as e:
        logger.exception("Error running seat sniper: %s", e)
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_sniper()
