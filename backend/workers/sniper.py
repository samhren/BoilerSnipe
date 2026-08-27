"""
Seat Sniper
Lightweight seat checker that walks a rotating queue of tracked CRNs
continuously, pacing itself against Purdue's rate limiter.

Rate limiting
-------------
Purdue's limiter on selfservice.mypurdue.purdue.edu is a *quota*, not a rate:
measured 2026-08-27 it allows ~90 requests per ~95-second sliding window and
then serves a 519-byte HTTP 200 "too many requests" page. Three independent
measurements blocked at exactly 90 successes regardless of spacing, so what
matters is cumulative count, not delay between requests. The limiter is
IP-keyed - a fresh container with a new `requests.Session` and no cookies
inherited the worker's block - so rotating sessions or cookies buys nothing.
Recovery once we go idle is ~9-20 seconds.

That ceiling sits near 0.95 req/s. Rather than hardcode a delay against an
undocumented limit that may differ per IP and may change, `AdaptivePacer`
converges on it with AIMD: multiplicative decrease on a block, additive
increase after a clean run.

Scheduling
----------
There is no "cycle that must complete". A single long-lived loop walks the
tracked-course queue indefinitely, issuing each check as the pacer releases a
token, reloading the queue every few minutes so new tracks are picked up
without a restart. The previous model - an APScheduler job every N minutes
that tried to sweep everything, truncated by a per-cycle request budget - could
not express a sweep that legitimately takes longer than the trigger interval.

Cancelled sections
------------------
A cancelled or removed CRN answers with a ~7 KB page reading "No detailed class
info" instead of the usual 13-16 KB page with a Registration Availability
table. That is indistinguishable from a parser bug unless we look for it, so
`SECTION_GONE` is its own status and a section is delisted only after several
consecutive such reads.
"""

import logging
import random
import statistics
import sys
import threading
import time
import requests
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
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
    a bug in our parser, BLOCKED means Purdue is throttling us, and
    SECTION_GONE means the section no longer exists. Collapsing them into
    `None` is what made the 2026-08-25 outage silent for 24 hours, and
    collapsing SECTION_GONE into PARSE_FAILED is what kept four cancelled
    sections silently unwatched for up to 21 days.
    """

    OK = "ok"
    BLOCKED = "blocked"
    NETWORK_ERROR = "network_error"
    PARSE_FAILED = "parse_failed"
    SECTION_GONE = "section_gone"


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
class SegmentSummary:
    """What one stretch of continuous queue-walking actually did.

    A segment is bounded by the course-list refresh interval, not by any
    notion of a completed sweep - it exists so the worker can pick up new
    tracks and report progress, and so tests can drive a bounded amount of
    work.
    """

    total_courses: int = 0
    attempted: int = 0
    checked: int = 0
    notifications_sent: int = 0
    sections_delisted: int = 0
    sections_relisted: int = 0
    breaker_tripped: bool = False
    waited_for_backoff_seconds: float = 0.0
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


# --- Page sniffing --------------------------------------------------------
#
# The observed block page is ~519 bytes and reads:
#   "We are sorry, but the site has received too many requests. Please try
#    again later."
# A real course detail page is ~12-16 KB, so a generous length ceiling keeps
# this from ever misfiring on a legitimate page that happens to contain the
# phrase.
BLOCK_PAGE_MARKERS = (
    "too many requests",
    "received too many requests",
)
BLOCK_PAGE_MAX_BYTES = 4096
BLOCKED_STATUS_CODES = (429, 503)

# A cancelled/removed CRN returns a 7,085-byte page whose body reads
#   <SPAN class="errortext">No detailed class information found</SPAN>
# where the Registration Availability table would otherwise be. Verified
# 2026-08-27 against CRNs 24805, 12076, 31469 and 14330, with CRN 21464 as a
# working control returning 15,652 bytes with the table present. The marker is
# the stable prefix, so a reworded suffix still matches.
SECTION_GONE_MARKERS = (
    "no detailed class info",
)

# --- Backoff --------------------------------------------------------------
#
# With the pacer holding us under the quota, backoff is a genuine safety net
# rather than the normal operating mode. The old 5-minute base was ~30x the
# measured ~9-20s recovery and cost roughly two thirds of available throughput.
BACKOFF_BASE_SECONDS = 15.0
BACKOFF_JITTER = 0.2  # +/- 20%

# Refilling the bucket multiplies a duration by a rate, so the token count
# lands a few ULPs short of a whole token: waiting 1/0.3 seconds at 0.3 req/s
# refills to 0.9999999999999999, not 1.0. Comparing exactly against 1.0 makes
# `acquire` spin, sleeping ever-shorter intervals and never releasing.
TOKEN_EPSILON = 1e-9
# Floor on any single wait, so no future rounding path can turn the pacer into
# a busy loop.
MIN_SLEEP_SECONDS = 1e-3


class AdaptivePacer:
    """AIMD token bucket converging on Purdue's undocumented request ceiling.

    Capacity is a single token and the bucket starts empty, so a process
    restart can never burst: the first request waits a full interval. On a
    block the rate is cut multiplicatively and the pacer idles for the measured
    recovery window; after a clean run of successes it creeps back up.

    `clock` and `sleeper` are injectable so tests can drive it on a virtual
    clock instead of waiting in real time.
    """

    CAPACITY = 1.0

    def __init__(
        self,
        start_rate: float,
        min_rate: float,
        max_rate: float,
        recovery_seconds: float,
        decrease_factor: float,
        increase_step: float,
        increase_after: int,
        clock=time.monotonic,
        sleeper=time.sleep,
    ):
        if min_rate <= 0:
            raise ValueError("min_rate must be positive")
        if max_rate < min_rate:
            raise ValueError("max_rate must be >= min_rate")

        self.min_rate = min_rate
        self.max_rate = max_rate
        self.recovery_seconds = max(0.0, recovery_seconds)
        self.decrease_factor = decrease_factor
        self.increase_step = increase_step
        self.increase_after = max(1, increase_after)
        self.clock = clock
        self.sleeper = sleeper

        self._lock = threading.Lock()
        self._rate = self._clamp(start_rate)
        self._tokens = 0.0
        self._last_refill: Optional[float] = None
        self._not_before: Optional[float] = None
        self._consecutive_ok = 0
        self.blocks_observed = 0

    def _clamp(self, rate: float) -> float:
        return max(self.min_rate, min(self.max_rate, rate))

    @property
    def rate(self) -> float:
        with self._lock:
            return self._rate

    @property
    def consecutive_successes(self) -> int:
        with self._lock:
            return self._consecutive_ok

    def acquire(self) -> float:
        """Block until one request may be issued. Returns seconds waited."""
        waited = 0.0
        while True:
            with self._lock:
                now = self.clock()
                if self._last_refill is None:
                    self._last_refill = now
                elapsed = max(0.0, now - self._last_refill)
                self._last_refill = now
                self._tokens = min(self.CAPACITY, self._tokens + elapsed * self._rate)

                wait = 0.0
                if self._not_before is not None:
                    if now >= self._not_before:
                        self._not_before = None
                    else:
                        wait = self._not_before - now

                if wait <= 0.0:
                    if self._tokens >= 1.0 - TOKEN_EPSILON:
                        self._tokens = max(0.0, self._tokens - 1.0)
                        return waited
                    wait = (1.0 - self._tokens) / self._rate

            wait = max(wait, MIN_SLEEP_SECONDS)
            self.sleeper(wait)
            waited += wait

    def record_success(self) -> Optional[Tuple[float, float]]:
        """Note a clean response. Returns (old, new) rate if it increased."""
        with self._lock:
            self._consecutive_ok += 1
            if self._consecutive_ok < self.increase_after:
                return None
            self._consecutive_ok = 0
            old = self._rate
            self._rate = self._clamp(self._rate + self.increase_step)
            return (old, self._rate) if self._rate != old else None

    def record_block(self) -> Tuple[float, float]:
        """Note a throttle. Cuts the rate and idles for the recovery window."""
        with self._lock:
            self.blocks_observed += 1
            self._consecutive_ok = 0
            old = self._rate
            self._rate = self._clamp(self._rate * self.decrease_factor)
            now = self.clock()
            self._tokens = 0.0
            self._last_refill = now
            self._not_before = now + self.recovery_seconds
            return old, self._rate

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            return {
                "rate": self._rate,
                "consecutive_successes": self._consecutive_ok,
                "blocks_observed": self.blocks_observed,
            }


def build_pacer(**overrides) -> AdaptivePacer:
    """An `AdaptivePacer` configured from settings."""
    kwargs = dict(
        start_rate=settings.SNIPER_PACER_START_RATE,
        min_rate=settings.SNIPER_PACER_MIN_RATE,
        max_rate=settings.SNIPER_PACER_MAX_RATE,
        recovery_seconds=settings.SNIPER_PACER_RECOVERY_SECONDS,
        decrease_factor=settings.SNIPER_PACER_DECREASE_FACTOR,
        increase_step=settings.SNIPER_PACER_INCREASE_STEP,
        increase_after=settings.SNIPER_PACER_INCREASE_AFTER,
    )
    kwargs.update(overrides)
    return AdaptivePacer(**kwargs)


# --- Cross-process-lifetime state ----------------------------------------
#
# `SeatSniper` is rebuilt periodically so its database session stays fresh, so
# per-instance state resets and buys nothing. The worker process is long-lived,
# so the pacer, backoff, rotation and sweep accounting live at module scope
# where they actually survive.
class _SniperRuntimeState:
    """Pacer, backoff, rotation and sweep state shared across SeatSnipers."""

    def __init__(self):
        self._lock = threading.Lock()
        self.pacer = build_pacer()
        self.backoff_until: Optional[datetime] = None
        self.backoff_level: int = 0
        self.rotation_offset: int = 0
        self.last_success_at: Optional[datetime] = None
        self.sweep_started_at: Optional[float] = None
        self.sweep_checks: int = 0
        self.last_sweep_seconds: Optional[float] = None
        self.delisted_recheck_at: Optional[float] = None

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
        """Escalate backoff one level. Returns the delay applied, in seconds."""
        now = now or datetime.now()
        with self._lock:
            self.backoff_level += 1
            raw = BACKOFF_BASE_SECONDS * (2 ** (self.backoff_level - 1))
            capped = min(raw, settings.SNIPER_BACKOFF_MAX_SECONDS)
            jittered = capped * random.uniform(1 - BACKOFF_JITTER, 1 + BACKOFF_JITTER)
            jittered = max(0.0, min(jittered, settings.SNIPER_BACKOFF_MAX_SECONDS))
            self.backoff_until = now + timedelta(seconds=jittered)
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
        """Move the queue cursor so the same tail is not starved forever."""
        with self._lock:
            if total > 0:
                self.rotation_offset = (self.rotation_offset + by) % total

    def current_rotation(self, total: int) -> int:
        with self._lock:
            return self.rotation_offset % total if total > 0 else 0

    def note_sweep_progress(self, total_courses: int, now: float) -> Optional[float]:
        """Count one check toward the current sweep.

        Returns the elapsed seconds of a sweep that just completed, meaning the
        queue cursor has visited every tracked course once since the last
        completion, or None if the sweep is still in progress.
        """
        with self._lock:
            if self.sweep_started_at is None:
                self.sweep_started_at = now
                self.sweep_checks = 0
            self.sweep_checks += 1
            if total_courses <= 0 or self.sweep_checks < total_courses:
                return None
            elapsed = now - self.sweep_started_at
            self.sweep_started_at = now
            self.sweep_checks = 0
            self.last_sweep_seconds = elapsed
            return elapsed

    def due_for_delisted_recheck(self, now: float) -> bool:
        """Whether the low-frequency delisted-course tier should run now."""
        with self._lock:
            interval = max(0, settings.SNIPER_DELISTED_RECHECK_SECONDS)
            if self.delisted_recheck_at is None:
                self.delisted_recheck_at = now
                return True
            if now - self.delisted_recheck_at < interval:
                return False
            self.delisted_recheck_at = now
            return True

    def reset(self) -> None:
        """Test hook - drop all state and rebuild the pacer from settings."""
        with self._lock:
            self.pacer = build_pacer()
            self.backoff_until = None
            self.backoff_level = 0
            self.rotation_offset = 0
            self.last_success_at = None
            self.sweep_started_at = None
            self.sweep_checks = 0
            self.last_sweep_seconds = None
            self.delisted_recheck_at = None


runtime_state = _SniperRuntimeState()


def looks_like_block_page(body: str) -> bool:
    """Whether a 200 response body is really Purdue's rate-limit notice."""
    if not body:
        return False
    if len(body.encode("utf-8", errors="ignore")) > BLOCK_PAGE_MAX_BYTES:
        return False
    lowered = body.lower()
    return any(marker in lowered for marker in BLOCK_PAGE_MARKERS)


def looks_like_missing_section(body: str) -> bool:
    """Whether a 200 response body is Purdue's "section does not exist" page."""
    if not body:
        return False
    lowered = body.lower()
    return any(marker in lowered for marker in SECTION_GONE_MARKERS)


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

    # --- HTTP -------------------------------------------------------------

    def check_seat_availability(self, crn: str, term_code: str) -> SeatCheckResult:
        """
        Check seat availability for a specific CRN.

        Returns:
            SeatCheckResult whose status distinguishes a successful read from a
            throttle, a network failure, a cancelled section, and a page we
            could not parse.
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

            # A cancelled section also answers 200, with a short page carrying
            # no availability table. Check before parsing so it never lands in
            # PARSE_FAILED and hides a genuine parser bug.
            if looks_like_missing_section(response.text):
                return SeatCheckResult(
                    CheckStatus.SECTION_GONE,
                    detail="HTTP 200 'No detailed class info' page",
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

    # --- Persistence ------------------------------------------------------

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

    def mark_section_present(self, course: Course) -> bool:
        """Clear cancellation state after a page that parsed. Returns True on relist."""
        relisted = False

        if course.section_gone_streak:
            course.section_gone_streak = 0

        if not course.is_listed:
            course.is_listed = True
            course.delisted_at = None
            relisted = True

        return relisted

    def mark_section_gone(self, course: Course, tracks: Sequence[Track]) -> bool:
        """Record one "No detailed class info" read. Returns True on delist.

        Banner returns that page transiently, so a section is only treated as
        cancelled once the streak clears the configured threshold.
        """
        threshold = max(1, settings.SNIPER_SECTION_GONE_THRESHOLD)
        # Capped: once delisted the hourly recheck tier keeps landing here, and
        # the count past the threshold carries no information.
        course.section_gone_streak = min(threshold, (course.section_gone_streak or 0) + 1)
        streak = course.section_gone_streak

        if not course.is_listed:
            # Already delisted; the low-frequency recheck tier keeps the streak
            # ticking but there is nothing new to announce.
            self.db.commit()
            return False

        if streak < threshold:
            logger.warning(
                "CRN %s (%s): section detail page missing (%d/%d consecutive) - "
                "not delisting yet.",
                course.crn, course.course_code, streak, threshold,
            )
            self.db.commit()
            return False

        course.is_listed = False
        course.delisted_at = datetime.now()
        self.db.commit()

        logger.error(
            "CRN %s (%s): SECTION CANCELLED - %d consecutive 'No detailed class "
            "info' responses. Delisted; %d track(s) will stop being checked.",
            course.crn, course.course_code, streak, len(tracks),
        )

        for track in tracks:
            self.notify_section_cancelled(track)

        return True

    # --- Notifications ----------------------------------------------------

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

    def already_notified_cancelled(self, user_id: int, course_id: int) -> bool:
        """Whether this user has already been told this section was cancelled.

        Guards against re-notifying on every recheck. Only a *sent* log counts,
        so a delivery failure is still retried.
        """
        existing = self.db.query(NotificationLog.id).filter(
            NotificationLog.user_id == user_id,
            NotificationLog.course_id == course_id,
            NotificationLog.notification_type == "section_cancelled",
            NotificationLog.status == "sent",
        ).first()
        return existing is not None

    def notify_section_cancelled(self, track: Track) -> bool:
        """Tell one user their tracked section is gone, at most once."""
        try:
            if self.already_notified_cancelled(track.user_id, track.course_id):
                return False
        except Exception as e:
            logger.exception("Error checking cancellation notification log: %s", e)
            return False

        self.send_notification(track, "section_cancelled", 0)
        return True

    def send_notification(self, track: Track, notification_type: str, seats: int):
        """
        Send notification via Email.

        Args:
            track: The Track object
            notification_type: "seat_open", "seat_closed" or "section_cancelled"
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
            elif notification_type == "section_cancelled":
                subject = f"🚫 Section No Longer Offered: {course.course_code}"
                message = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #b91c1c; margin-top: 0;">🚫 Section No Longer Offered</h2>
                    <p style="font-size: 16px;">Purdue has removed <strong>{course.course_code} - {course.title}</strong> from the schedule, so we can no longer watch it for you.</p>

                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>CRN:</strong> {course.crn}</p>
                        <p style="margin: 5px 0;"><strong>Term:</strong> {course.term_name or course.term_code}</p>
                        <p style="margin: 5px 0;"><strong>Status:</strong> Section cancelled or removed</p>
                    </div>

                    <p><strong>You will not receive any more seat alerts for this CRN.</strong> If you still need the course, search for another section and track that instead.</p>

                    <a href="https://boilersnipe.com/search" style="display: inline-block; background-color: #cfb991; color: #000; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Find another section</a>
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

    # --- Queue ------------------------------------------------------------

    def load_tracked_courses(self, listed: bool = True) -> Dict[Tuple[str, str], List[Track]]:
        """Active tracks for the current term, grouped by term-scoped CRN.

        Old-term tracks stay in the database but do not consume worker time.
        `listed=False` selects the delisted courses handled by the
        low-frequency recheck tier.
        """
        active_tracks = self.db.query(Track).join(Course).filter(
            Track.is_active == True,
            Course.term_code == settings.CURRENT_TERM_CODE,
            Course.is_listed == (True if listed else False),
        ).all()

        grouped: Dict[Tuple[str, str], List[Track]] = {}
        for track in active_tracks:
            course_key = (track.course.term_code, track.course.crn)
            grouped.setdefault(course_key, []).append(track)
        return grouped

    def _ordered_course_keys(self, crn_tracks: Dict) -> List[Tuple[str, str]]:
        """Course keys in a stable order, rotated to where we left off.

        Sorting first makes the rotation meaningful: without a deterministic
        base order, "start where we left off" is not well defined.
        """
        keys = sorted(crn_tracks.keys())
        if not keys:
            return keys
        offset = runtime_state.current_rotation(len(keys))
        return keys[offset:] + keys[:offset]

    # --- The continuous walk ---------------------------------------------

    def check_one_course(
        self, course: Course, tracks: Sequence[Track], summary: SegmentSummary
    ) -> SeatCheckResult:
        """Issue one paced check and apply everything it implies."""
        runtime_state.pacer.acquire()

        result = self.check_seat_availability(course.crn, course.term_code)
        summary.attempted += 1
        summary.record(result.status)

        if result.ok:
            raised = runtime_state.pacer.record_success()
            if raised:
                logger.info(
                    "Pacer rate increased %.3f -> %.3f req/s after a clean run.",
                    raised[0], raised[1],
                )
            if runtime_state.record_success():
                logger.info("Sniper backoff cleared after a successful check.")

            seat_data = result.data
            new_seats = seat_data['seats_remaining']
            logger.info(
                "CRN %s (%s): %d/%d seats available",
                course.crn, course.course_code, new_seats, seat_data['seats_capacity'],
            )

            if self.mark_section_present(course):
                summary.sections_relisted += 1
                logger.warning(
                    "CRN %s (%s): RELISTED - the section detail page is back, "
                    "resuming seat checks.",
                    course.crn, course.course_code,
                )

            self.update_course_seats(course, seat_data)

            for track in tracks:
                old_track_seats = track.last_seats
                self.process_track_notifications(track, old_track_seats, new_seats)

                if (old_track_seats == 0 and new_seats > 0 and track.notify_on_open) or \
                   (old_track_seats > 0 and new_seats == 0 and track.notify_on_close):
                    summary.notifications_sent += 1

            summary.checked += 1
            return result

        if result.status is CheckStatus.BLOCKED:
            old_rate, new_rate = runtime_state.pacer.record_block()
            logger.error(
                "CRN %s (%s): BLOCKED by Purdue rate limiting - %s. Pacer rate "
                "cut %.3f -> %.3f req/s, idling %.0fs.",
                course.crn, course.course_code, result.detail,
                old_rate, new_rate, runtime_state.pacer.recovery_seconds,
            )
        elif result.status is CheckStatus.NETWORK_ERROR:
            logger.warning(
                "CRN %s (%s): network error - %s",
                course.crn, course.course_code, result.detail,
            )
        elif result.status is CheckStatus.SECTION_GONE:
            if self.mark_section_gone(course, tracks):
                summary.sections_delisted += 1
        else:
            logger.error(
                "CRN %s (%s): PARSE FAILED on an apparently valid page - %s",
                course.crn, course.course_code, result.detail,
            )

        return result

    def run_queue_segment(
        self,
        max_courses: Optional[int] = None,
        deadline: Optional[float] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> SegmentSummary:
        """Walk the rotating tracked-course queue until bounded out.

        The queue wraps: this is a continuous walk, not a cycle that must
        complete. `max_courses` and `deadline` exist so the caller can come up
        for air - to reload the queue, run the delisted tier, and report
        progress - and so tests can drive a bounded amount of work.

        `deadline` is read off the pacer's clock, which in production is
        `time.monotonic`. The pacer is what actually consumes wall-clock time
        here, so sharing its clock keeps the two from disagreeing.
        """
        summary = SegmentSummary()

        # A tripped breaker means Purdue is actively refusing us. Wait it out
        # rather than grinding requests into the wall, which is what kept the
        # block open during the 2026-08-25 incident.
        backoff_remaining = runtime_state.backoff_remaining_seconds()
        if backoff_remaining > 0:
            summary.waited_for_backoff_seconds = backoff_remaining
            logger.warning(
                "Sniper backoff active (level %d): pausing %.1fs before "
                "contacting Purdue again.",
                runtime_state.backoff_level, backoff_remaining,
            )
            time.sleep(backoff_remaining)

        crn_tracks = self.load_tracked_courses()
        if not crn_tracks:
            logger.info("No active tracks found.")
            return summary

        ordered_keys = self._ordered_course_keys(crn_tracks)
        total = len(ordered_keys)
        summary.total_courses = total

        logger.info(
            "Walking %d tracked course(s) at %.3f req/s (queue position %d).",
            total, runtime_state.pacer.rate, runtime_state.current_rotation(total),
        )

        consecutive_failures = 0
        max_failures = max(1, settings.SNIPER_MAX_CONSECUTIVE_FAILURES)
        index = 0

        while True:
            if max_courses is not None and index >= max_courses:
                break
            if deadline is not None and runtime_state.pacer.clock() >= deadline:
                break
            if stop_event is not None and stop_event.is_set():
                break

            course_key = ordered_keys[index % total]
            tracks = crn_tracks[course_key]
            course = tracks[0].course  # All tracks share the same course

            result = self.check_one_course(course, tracks, summary)
            index += 1
            runtime_state.advance_rotation(1, total)

            sweep_seconds = runtime_state.note_sweep_progress(
                total, runtime_state.pacer.clock()
            )
            if sweep_seconds is not None:
                self._log_sweep_complete(sweep_seconds, total)

            if result.is_rate_limit_signal:
                consecutive_failures += 1
            else:
                consecutive_failures = 0

            if consecutive_failures >= max_failures:
                summary.breaker_tripped = True
                delay_seconds = runtime_state.trip_backoff()
                logger.error(
                    "CIRCUIT BREAKER TRIPPED: %d consecutive blocked/network "
                    "failures. Pausing the queue walk and backing off for "
                    "%.1fs (level %d) before contacting Purdue again.",
                    consecutive_failures, delay_seconds, runtime_state.backoff_level,
                )
                break

        self._log_summary(summary)
        return summary

    def recheck_delisted_courses(
        self, stop_event: Optional[threading.Event] = None
    ) -> SegmentSummary:
        """Low-frequency tier: give delisted sections a chance to come back.

        The main walk filters on `is_listed == True`, so without this a section
        delisted once could never be relisted even if Purdue restored it.
        """
        summary = SegmentSummary()
        crn_tracks = self.load_tracked_courses(listed=False)
        if not crn_tracks:
            return summary

        summary.total_courses = len(crn_tracks)
        logger.info(
            "Rechecking %d delisted course(s) for relisting.", summary.total_courses
        )

        for course_key in sorted(crn_tracks.keys()):
            if stop_event is not None and stop_event.is_set():
                break
            tracks = crn_tracks[course_key]
            self.check_one_course(tracks[0].course, tracks, summary)

        if summary.sections_relisted:
            logger.warning(
                "Delisted recheck relisted %d section(s).", summary.sections_relisted
            )
        else:
            logger.info(
                "Delisted recheck complete: %d of %d still missing.",
                summary.status_counts.get(CheckStatus.SECTION_GONE, 0),
                summary.total_courses,
            )
        return summary

    # --- Observability ----------------------------------------------------

    def staleness_percentiles(self) -> Optional[Dict[str, float]]:
        """Age in seconds of the last successful check, across tracked courses.

        Median staleness is the number that matters: it is what a user actually
        experiences as "how out of date is my seat count".
        """
        courses = self.db.query(Course).join(Track).filter(
            Track.is_active == True,
            Course.term_code == settings.CURRENT_TERM_CODE,
            Course.is_listed == True,
        ).distinct().all()

        if not courses:
            return None

        now = datetime.now()
        ages: List[float] = []
        never_checked = 0
        for course in courses:
            if course.last_checked is None:
                never_checked += 1
                continue
            reference = now if course.last_checked.tzinfo is None else datetime.now(course.last_checked.tzinfo)
            ages.append(max(0.0, (reference - course.last_checked).total_seconds()))

        if not ages:
            return {"courses": len(courses), "never_checked": never_checked}

        ages.sort()
        return {
            "courses": len(courses),
            "never_checked": never_checked,
            "p50_seconds": statistics.median(ages),
            "p90_seconds": ages[min(len(ages) - 1, int(round(0.9 * (len(ages) - 1))))],
            "max_seconds": ages[-1],
        }

    def log_staleness(self) -> None:
        """Emit the staleness line. Baseline before the pacer: p50 16m40s, p90 31m49s."""
        stats = self.staleness_percentiles()
        if not stats:
            return
        if "p50_seconds" not in stats:
            logger.warning(
                "Staleness: none of %d tracked course(s) has ever been checked "
                "successfully.",
                stats["courses"],
            )
            return

        logger.info(
            "Staleness across %d tracked course(s): p50 %.1fm, p90 %.1fm, "
            "oldest %.1fm, never checked %d. Pacer at %.3f req/s.",
            stats["courses"], stats["p50_seconds"] / 60.0,
            stats["p90_seconds"] / 60.0, stats["max_seconds"] / 60.0,
            stats["never_checked"], runtime_state.pacer.rate,
        )

    def _log_sweep_complete(self, seconds: float, total_courses: int) -> None:
        logger.info(
            "Full sweep complete: %d course(s) in %.1fm (%.3f req/s pacer rate).",
            total_courses, seconds / 60.0, runtime_state.pacer.rate,
        )

    def _log_summary(self, summary: SegmentSummary) -> None:
        """Emit the end-of-segment summary, loudly when the segment was abnormal."""
        detail = (
            f"checked {summary.checked}/{summary.attempted} attempted across "
            f"{summary.total_courses} tracked course(s), "
            f"notifications sent {summary.notifications_sent}"
        )
        if summary.sections_delisted:
            detail += f", {summary.sections_delisted} section(s) delisted"
        if summary.sections_relisted:
            detail += f", {summary.sections_relisted} section(s) relisted"

        # The failure mode that hid the 2026-08-25 outage: checked == 0 with
        # courses to check looked exactly like a normal cycle in the logs. It
        # never will again.
        if summary.attempted > 0 and summary.checked == 0:
            dominant = summary.dominant_failure
            reason = dominant.value if dominant else "no checks attempted"
            logger.critical(
                "SNIPER NOT FUNCTIONING: 0 of %d attempted checks succeeded "
                "against %d tracked course(s). Dominant failure: %s. No "
                "seat-open notifications can be sent while this persists. (%s)",
                summary.attempted, summary.total_courses, reason, detail,
            )
            return

        failures = summary.attempted - summary.checked
        if failures:
            logger.warning("Queue segment complete with %d failure(s): %s", failures, detail)
        else:
            logger.info("Queue segment complete: %s", detail)

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


def run_sniper_forever(stop_event: Optional[threading.Event] = None) -> None:
    """Walk the tracked-course queue continuously until asked to stop.

    Each iteration builds a fresh SeatSniper - so the database session stays
    healthy and the tracked-course list is reloaded - and walks the queue for
    up to `SNIPER_COURSE_REFRESH_SECONDS`. Pacer, backoff, rotation and sweep
    accounting live in `runtime_state` and survive across iterations.
    """
    refresh_seconds = max(30, settings.SNIPER_COURSE_REFRESH_SECONDS)
    logger.info(
        "Seat sniper starting continuous walk: refreshing the course queue "
        "every %ds, pacer starting at %.3f req/s (clamped to %.2f-%.2f).",
        refresh_seconds, runtime_state.pacer.rate,
        settings.SNIPER_PACER_MIN_RATE, settings.SNIPER_PACER_MAX_RATE,
    )

    while stop_event is None or not stop_event.is_set():
        try:
            with SeatSniper(use_proxy=False) as sniper:
                if runtime_state.due_for_delisted_recheck(runtime_state.pacer.clock()):
                    sniper.recheck_delisted_courses(stop_event=stop_event)

                summary = sniper.run_queue_segment(
                    deadline=runtime_state.pacer.clock() + refresh_seconds,
                    stop_event=stop_event,
                )
                sniper.log_staleness()

                if summary.total_courses == 0:
                    # Nothing to do; do not spin.
                    _interruptible_sleep(refresh_seconds, stop_event)

        except Exception as e:
            logger.exception("Seat sniper loop error, retrying shortly: %s", e)
            _interruptible_sleep(30, stop_event)

    logger.info("Seat sniper continuous walk stopped.")


def _interruptible_sleep(seconds: float, stop_event: Optional[threading.Event]) -> None:
    if stop_event is None:
        time.sleep(seconds)
    else:
        stop_event.wait(seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_sniper_forever()
