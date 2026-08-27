"""Tests for the seat sniper's pacing, resilience and cancelled-section handling.

Every HTTP call is mocked and the pacer runs on a virtual clock, so nothing here
waits or touches the network.

Two incidents shape these tests. The 2026-08-25 outage was invisible: Purdue
returned HTTP 200 block pages for 24 hours and the sniper reported them the same
way it reports a parse miss. And as of 2026-08-27 four tracked CRNs had been
silently dead for up to 21 days, because a cancelled section's detail page also
classified as a parse failure.
"""

import pytest
import requests

from app import models
from app.config import settings
from workers import sniper as sniper_module
from workers.sniper import (
    AdaptivePacer,
    CheckStatus,
    SeatSniper,
    build_pacer,
    looks_like_block_page,
    looks_like_missing_section,
    runtime_state,
)


class FakeResponse:
    """Stand-in for `requests.Response` covering what the sniper touches."""

    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error", response=self)


class FakeSession:
    """Replays a scripted sequence of responses or exceptions."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}
        self.proxies = {}

    def get(self, url, **kwargs):
        self.calls.append(url)
        if not self.responses:
            raise AssertionError(f"unexpected extra request to {url}")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        pass


class VirtualClock:
    """A clock whose only way to advance is sleeping.

    The pacer's whole job is deciding how long to wait, so driving it on real
    time would make every assertion about that a race. Here `elapsed` is exactly
    the pacer's own accounting.
    """

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    @property
    def elapsed(self):
        return self.now - 1000.0


@pytest.fixture
def clock():
    return VirtualClock()


@pytest.fixture
def db_session():
    """A real in-memory SQLite session, wired into the module the sniper uses."""
    from app.database import Base, engine, SessionLocal

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def no_sleep(monkeypatch):
    """Backoff waits are real in production; tests should not sit through them."""
    slept = []
    monkeypatch.setattr(sniper_module.time, "sleep", slept.append)
    return slept


@pytest.fixture
def fast_pacer(clock):
    """Install a virtual-clock pacer as the process-wide one.

    Tests that care about scheduling rather than pacing get a pacer that never
    blocks real time but still records every wait it imposed.
    """
    runtime_state.pacer = build_pacer(clock=clock.monotonic, sleeper=clock.sleep)
    return runtime_state.pacer


@pytest.fixture
def sent_emails(monkeypatch):
    """Capture outbound email instead of calling Resend."""
    sent = []

    def fake_send(to_email, subject, html_content):
        sent.append((to_email, subject, html_content))
        return True, None

    monkeypatch.setattr(
        "workers.notifier.send_email_notification", fake_send, raising=True
    )
    return sent


def make_sniper(responses):
    sniper = SeatSniper()
    sniper.session = FakeSession(responses)
    return sniper


def seed_tracks(session, count, term_code=None, users=1, is_listed=True):
    """Create `count` distinct tracked courses, each tracked by every user."""
    term_code = term_code or settings.CURRENT_TERM_CODE
    user_rows = []
    for u in range(users):
        user = models.User(email=f"student{u}@purdue.edu", hashed_password="x")
        session.add(user)
        user_rows.append(user)
    session.flush()

    courses = []
    for i in range(count):
        course = models.Course(
            crn=f"{10000 + i}",
            course_code=f"CS {10000 + i}",
            title=f"Course {i}",
            term_code=term_code,
            is_listed=is_listed,
            seats_capacity=27,
            seats_available=27,
            seats_remaining=0,
        )
        session.add(course)
        session.flush()
        courses.append(course)
        for user in user_rows:
            session.add(models.Track(
                user_id=user.id,
                course_id=course.id,
                is_active=True,
                notify_on_open=False,
                notify_on_close=False,
                last_seats=0,
            ))
    session.commit()
    return courses


# --- Outcome classification ----------------------------------------------

def test_block_page_on_200_is_classified_blocked(db_session, block_page_html):
    """The exact failure that caused the 2026-08-25 outage."""
    sniper = make_sniper([FakeResponse(200, block_page_html)])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.BLOCKED
    assert result.data is None
    assert result.is_rate_limit_signal


@pytest.mark.parametrize("status_code", [429, 503])
def test_rate_limit_status_codes_are_blocked(db_session, status_code):
    sniper = make_sniper([FakeResponse(status_code, "")])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.BLOCKED
    assert str(status_code) in result.detail


def test_real_course_page_parses(db_session, course_detail_html):
    sniper = make_sniper([FakeResponse(200, course_detail_html)])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.OK
    assert result.data["seats_capacity"] == 27
    assert result.data["seats_available"] == 27
    assert result.data["seats_remaining"] == 0
    assert result.data["last_checked"] is not None


def test_cross_list_seats_row_caps_availability(db_session, cross_list_html):
    """Cross-listed sections are limited by the aggregate cap, not their own row."""
    sniper = make_sniper([FakeResponse(200, cross_list_html)])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.OK
    # Own Seats row says 5 remaining; the cross-list cap allows only 2.
    assert result.data["seats_remaining"] == 2
    assert result.data["seats_capacity"] == 50


def test_cross_list_row_is_ignored_when_less_restrictive(db_session, cross_list_html):
    html = cross_list_html.replace(
        '<td CLASS="dddefault">50</td>\n<td CLASS="dddefault">48</td>\n<td CLASS="dddefault">2</td>',
        '<td CLASS="dddefault">50</td>\n<td CLASS="dddefault">30</td>\n<td CLASS="dddefault">20</td>',
    )
    sniper = make_sniper([FakeResponse(200, html)])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.OK
    assert result.data["seats_remaining"] == 5
    assert result.data["seats_capacity"] == 30


def test_unparseable_page_is_parse_failed_not_blocked(db_session):
    """A parser bug must stay distinguishable from a throttle."""
    page = "<html><body>" + ("<p>real content</p>" * 500) + "</body></html>"
    sniper = make_sniper([FakeResponse(200, page)])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.PARSE_FAILED
    assert not result.is_rate_limit_signal


@pytest.mark.parametrize("exc", [
    requests.exceptions.ReadTimeout("read timed out"),
    requests.exceptions.ConnectionError("RemoteDisconnected"),
])
def test_transport_failures_are_network_errors(db_session, exc):
    sniper = make_sniper([exc])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.NETWORK_ERROR
    assert result.is_rate_limit_signal


def test_server_error_is_network_error_not_blocked(db_session):
    sniper = make_sniper([FakeResponse(500, "boom")])
    result = sniper.check_seat_availability("12946", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.NETWORK_ERROR


def test_cancelled_section_is_section_gone_not_parse_failed(db_session, section_gone_html):
    """The real page for CRN 24805. Misfiling it as PARSE_FAILED is the bug."""
    sniper = make_sniper([FakeResponse(200, section_gone_html)])
    result = sniper.check_seat_availability("24805", settings.CURRENT_TERM_CODE)

    assert result.status is CheckStatus.SECTION_GONE
    assert result.status is not CheckStatus.PARSE_FAILED
    assert not result.is_rate_limit_signal
    assert result.data is None


# --- Page sniffing --------------------------------------------------------

def test_looks_like_block_page_matches_case_insensitively(block_page_html):
    assert looks_like_block_page(block_page_html)
    assert looks_like_block_page(block_page_html.upper())


def test_looks_like_block_page_ignores_full_size_pages(course_detail_html):
    """The length ceiling keeps a real page from ever matching by accident."""
    assert not looks_like_block_page(course_detail_html)
    assert not looks_like_block_page(course_detail_html + "too many requests")
    assert not looks_like_block_page("")


def test_missing_section_sniffing_does_not_match_a_live_page(
    section_gone_html, course_detail_html, block_page_html
):
    assert looks_like_missing_section(section_gone_html)
    assert looks_like_missing_section(section_gone_html.upper())
    assert not looks_like_missing_section(course_detail_html)
    assert not looks_like_missing_section(block_page_html)
    assert not looks_like_missing_section("")


# --- The adaptive pacer ---------------------------------------------------

def test_pacer_starts_empty_and_does_not_burst(clock):
    """A process restart must never fire a burst into an active quota."""
    pacer = AdaptivePacer(
        start_rate=0.75, min_rate=0.3, max_rate=0.9, recovery_seconds=12.0,
        decrease_factor=0.7, increase_step=0.02, increase_after=25,
        clock=clock.monotonic, sleeper=clock.sleep,
    )

    # Even the very first acquire waits a full interval.
    waited = pacer.acquire()
    assert waited == pytest.approx(1 / 0.75, rel=1e-6)

    for _ in range(9):
        pacer.acquire()

    # Ten requests at 0.75 req/s is ten intervals, not an instant burst.
    assert clock.elapsed == pytest.approx(10 / 0.75, rel=1e-6)


def test_pacer_does_not_bank_idle_time_into_a_burst(clock):
    """Capacity is one token: idling for an hour still buys one free request."""
    pacer = AdaptivePacer(
        start_rate=0.5, min_rate=0.3, max_rate=0.9, recovery_seconds=0.0,
        decrease_factor=0.7, increase_step=0.02, increase_after=25,
        clock=clock.monotonic, sleeper=clock.sleep,
    )
    pacer.acquire()
    clock.now += 3600  # a long idle stretch

    assert pacer.acquire() == 0.0, "the single banked token is free"
    assert pacer.acquire() == pytest.approx(2.0), "the second one is not"


def test_pacer_decreases_multiplicatively_on_a_block(clock):
    pacer = AdaptivePacer(
        start_rate=0.75, min_rate=0.3, max_rate=0.9, recovery_seconds=12.0,
        decrease_factor=0.7, increase_step=0.02, increase_after=25,
        clock=clock.monotonic, sleeper=clock.sleep,
    )

    old, new = pacer.record_block()
    assert old == pytest.approx(0.75)
    assert new == pytest.approx(0.525)
    assert pacer.rate == pytest.approx(0.525)

    # And it idles for the measured recovery window before the next request.
    pacer.acquire()
    assert clock.elapsed >= 12.0


def test_pacer_increases_additively_after_a_clean_streak(clock):
    pacer = AdaptivePacer(
        start_rate=0.75, min_rate=0.3, max_rate=0.9, recovery_seconds=12.0,
        decrease_factor=0.7, increase_step=0.02, increase_after=25,
        clock=clock.monotonic, sleeper=clock.sleep,
    )

    for _ in range(24):
        assert pacer.record_success() is None, "must not creep up early"
    assert pacer.rate == pytest.approx(0.75)

    raised = pacer.record_success()
    assert raised == (pytest.approx(0.75), pytest.approx(0.77))
    assert pacer.consecutive_successes == 0, "the streak restarts after a raise"


def test_pacer_block_resets_the_success_streak(clock):
    pacer = AdaptivePacer(
        start_rate=0.75, min_rate=0.3, max_rate=0.9, recovery_seconds=1.0,
        decrease_factor=0.7, increase_step=0.02, increase_after=5,
        clock=clock.monotonic, sleeper=clock.sleep,
    )
    for _ in range(4):
        pacer.record_success()
    pacer.record_block()

    assert pacer.consecutive_successes == 0
    for _ in range(4):
        assert pacer.record_success() is None


def test_pacer_rate_is_clamped_to_the_configured_band(clock):
    pacer = AdaptivePacer(
        start_rate=0.75, min_rate=0.30, max_rate=0.90, recovery_seconds=0.0,
        decrease_factor=0.5, increase_step=0.5, increase_after=1,
        clock=clock.monotonic, sleeper=clock.sleep,
    )

    for _ in range(20):
        pacer.record_block()
    assert pacer.rate == pytest.approx(0.30), "never below the floor"

    for _ in range(20):
        pacer.record_success()
    assert pacer.rate == pytest.approx(0.90), "never above the ceiling"


def test_pacer_start_rate_outside_the_band_is_clamped(clock):
    high = AdaptivePacer(
        start_rate=5.0, min_rate=0.3, max_rate=0.9, recovery_seconds=0.0,
        decrease_factor=0.7, increase_step=0.02, increase_after=25,
        clock=clock.monotonic, sleeper=clock.sleep,
    )
    assert high.rate == pytest.approx(0.9)


def test_pacer_state_survives_across_two_sniper_constructions(
    db_session, no_sleep, fast_pacer, course_detail_html
):
    """Per-instance pacer state would reset every refresh and buy nothing."""
    seed_tracks(db_session, 2)
    blocked = FakeResponse(200, "too many requests")

    first = make_sniper([blocked, FakeResponse(200, course_detail_html)])
    first.run_queue_segment(max_courses=2)
    cut_rate = runtime_state.pacer.rate
    assert cut_rate == pytest.approx(settings.SNIPER_PACER_START_RATE * 0.70)

    # A brand new SeatSniper, as the continuous loop builds every refresh.
    second = make_sniper([FakeResponse(200, course_detail_html)] * 2)
    second.run_queue_segment(max_courses=2)

    assert runtime_state.pacer.rate == pytest.approx(cut_rate), \
        "the cut rate must carry over, not reset to the start rate"


def test_every_request_goes_through_the_pacer(
    db_session, no_sleep, fast_pacer, clock, course_detail_html
):
    seed_tracks(db_session, 5)
    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 5)
    sniper.run_queue_segment(max_courses=5)

    assert len(sniper.session.calls) == 5
    assert clock.elapsed == pytest.approx(5 / settings.SNIPER_PACER_START_RATE, rel=1e-6)


# --- Circuit breaker ------------------------------------------------------

def test_breaker_stops_the_walk_after_consecutive_failures(
    db_session, no_sleep, fast_pacer, monkeypatch
):
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 5)
    seed_tracks(db_session, 20)

    blocked = FakeResponse(200, "too many requests")
    sniper = make_sniper([blocked] * 20)
    summary = sniper.run_queue_segment(max_courses=20)

    assert summary.breaker_tripped
    assert summary.attempted == 5, "must stop at the threshold, not grind all 20"
    assert summary.checked == 0
    assert len(sniper.session.calls) == 5


def test_breaker_resets_on_an_interleaved_success(
    db_session, no_sleep, fast_pacer, monkeypatch, course_detail_html
):
    """Only *consecutive* failures trip the breaker."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    seed_tracks(db_session, 6)

    blocked = FakeResponse(200, "too many requests")
    ok = FakeResponse(200, course_detail_html)
    # fail, fail, ok, fail, fail, ok - never three in a row
    sniper = make_sniper([blocked, blocked, ok, blocked, blocked, ok])
    summary = sniper.run_queue_segment(max_courses=6)

    assert not summary.breaker_tripped
    assert summary.attempted == 6
    assert summary.checked == 2


def test_parse_failures_alone_do_not_trip_the_breaker(
    db_session, no_sleep, fast_pacer, monkeypatch
):
    """A parser bug is not a reason to stop talking to Purdue."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    seed_tracks(db_session, 5)

    page = "<html><body>" + ("<p>x</p>" * 500) + "</body></html>"
    sniper = make_sniper([FakeResponse(200, page)] * 5)
    summary = sniper.run_queue_segment(max_courses=5)

    assert not summary.breaker_tripped
    assert summary.attempted == 5
    assert summary.status_counts[CheckStatus.PARSE_FAILED] == 5


def test_cancelled_sections_alone_do_not_trip_the_breaker(
    db_session, no_sleep, fast_pacer, monkeypatch, section_gone_html
):
    """A run of cancelled sections is not a throttle and must not read as one."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    seed_tracks(db_session, 5)

    sniper = make_sniper([FakeResponse(200, section_gone_html)] * 5)
    summary = sniper.run_queue_segment(max_courses=5)

    assert not summary.breaker_tripped
    assert summary.status_counts[CheckStatus.SECTION_GONE] == 5
    assert runtime_state.pacer.rate == pytest.approx(settings.SNIPER_PACER_START_RATE), \
        "a dead CRN is not a reason to slow down"


# --- Backoff --------------------------------------------------------------

def test_backoff_escalates_in_seconds_and_is_capped(monkeypatch):
    """The old 5-minute base was ~30x the measured ~9-20s recovery."""
    monkeypatch.setattr(settings, "SNIPER_BACKOFF_MAX_SECONDS", 300.0)

    delays = [runtime_state.trip_backoff() for _ in range(8)]

    # Exponential from a 15 second base, with +/-20% jitter, capped at 300s.
    assert 12.0 <= delays[0] <= 18.0
    assert 24.0 <= delays[1] <= 36.0
    assert 48.0 <= delays[2] <= 72.0
    assert all(d <= 300.0 for d in delays)
    assert delays[-1] > 200.0
    assert runtime_state.backoff_level == 8


def test_backoff_persists_across_snipers_and_clears_after_success(
    db_session, no_sleep, fast_pacer, monkeypatch, course_detail_html
):
    """A fresh SeatSniper per refresh must still be suppressed."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    seed_tracks(db_session, 10)

    blocked = FakeResponse(200, "too many requests")

    # Trip the breaker and arm backoff.
    first = make_sniper([blocked] * 3)
    summary_one = first.run_queue_segment(max_courses=10)
    assert summary_one.breaker_tripped
    assert runtime_state.backoff_level == 1
    assert runtime_state.backoff_remaining_seconds() > 0

    # A brand new instance must wait the backoff out before its first request.
    second = make_sniper([FakeResponse(200, course_detail_html)] * 2)
    summary_two = second.run_queue_segment(max_courses=2)
    assert summary_two.waited_for_backoff_seconds > 0
    assert no_sleep, "the backoff must actually be waited out, not skipped"

    # And the first success clears it.
    assert runtime_state.backoff_level == 0
    assert runtime_state.backoff_remaining_seconds() == 0
    assert runtime_state.last_success_at is not None


# --- Rotation -------------------------------------------------------------

def test_rotation_visits_every_course_without_starving_the_tail(
    db_session, no_sleep, fast_pacer, course_detail_html
):
    """The queue cursor survives across segments, so no course is starved."""
    seed_tracks(db_session, 10)
    ok = FakeResponse(200, course_detail_html)

    seen = []
    for _ in range(5):  # five segments of 2 courses each
        sniper = make_sniper([ok] * 2)
        sniper.run_queue_segment(max_courses=2)
        seen.extend(url.split("crn_in=")[1] for url in sniper.session.calls)

    assert len(seen) == 10
    assert len(set(seen)) == 10, "every course visited exactly once across the pass"


def test_rotation_wraps_and_starts_the_next_pass(
    db_session, no_sleep, fast_pacer, course_detail_html
):
    """The walk is continuous: reaching the end of the queue starts over."""
    seed_tracks(db_session, 3)
    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 7)
    summary = sniper.run_queue_segment(max_courses=7)

    crns = [url.split("crn_in=")[1] for url in sniper.session.calls]
    assert summary.attempted == 7
    assert crns[:3] == crns[3:6], "the second pass repeats the first, in order"
    assert len(set(crns)) == 3


def test_a_segment_is_bounded_by_its_deadline(
    db_session, fast_pacer, clock, no_sleep, course_detail_html
):
    """The refresh deadline is what ends a segment, not a request budget."""
    seed_tracks(db_session, 50)
    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 50)

    # The pacer's virtual clock is the same one `run_queue_segment` reads.
    sniper.run_queue_segment(deadline=clock.monotonic() + 10.0)

    # At 0.75 req/s, ten seconds is room for about eight requests.
    assert 6 <= len(sniper.session.calls) <= 9


# --- Cancelled sections ---------------------------------------------------

def test_one_transient_section_gone_does_not_delist(
    db_session, no_sleep, fast_pacer, monkeypatch, section_gone_html, course_detail_html
):
    """Banner returns that page transiently; a single read must not delist."""
    monkeypatch.setattr(settings, "SNIPER_SECTION_GONE_THRESHOLD", 3)
    course = seed_tracks(db_session, 1)[0]

    sniper = make_sniper([
        FakeResponse(200, section_gone_html),
        FakeResponse(200, course_detail_html),
    ])
    sniper.run_queue_segment(max_courses=2)

    db_session.refresh(course)
    assert course.is_listed is True
    assert course.delisted_at is None
    assert course.section_gone_streak == 0, "a good read resets the streak"


def test_section_is_delisted_only_after_n_consecutive_misses(
    db_session, no_sleep, fast_pacer, monkeypatch, section_gone_html, sent_emails
):
    monkeypatch.setattr(settings, "SNIPER_SECTION_GONE_THRESHOLD", 3)
    course = seed_tracks(db_session, 1)[0]
    gone = FakeResponse(200, section_gone_html)

    for expected_streak in (1, 2):
        sniper = make_sniper([gone])
        summary = sniper.run_queue_segment(max_courses=1)
        db_session.refresh(course)
        assert course.is_listed is True
        assert course.section_gone_streak == expected_streak
        assert summary.sections_delisted == 0

    sniper = make_sniper([gone])
    summary = sniper.run_queue_segment(max_courses=1)

    db_session.refresh(course)
    assert course.is_listed is False
    assert course.delisted_at is not None
    assert summary.sections_delisted == 1


def test_delisted_course_leaves_the_main_queue(
    db_session, no_sleep, fast_pacer, monkeypatch, section_gone_html, sent_emails
):
    """Once delisted it must stop consuming the pacer's budget."""
    monkeypatch.setattr(settings, "SNIPER_SECTION_GONE_THRESHOLD", 1)
    courses = seed_tracks(db_session, 2)
    courses[0].is_listed = False
    courses[0].delisted_at = sniper_module.datetime.now()
    db_session.commit()

    sniper = make_sniper([FakeResponse(200, section_gone_html)])
    summary = sniper.run_queue_segment(max_courses=1)

    assert summary.total_courses == 1
    assert sniper.session.calls[0].endswith(courses[1].crn)


def test_a_delisted_course_that_parses_again_is_relisted(
    db_session, no_sleep, fast_pacer, course_detail_html
):
    """Without the recheck tier a delisted section could never come back."""
    course = seed_tracks(db_session, 1)[0]
    course.is_listed = False
    course.delisted_at = sniper_module.datetime.now()
    course.section_gone_streak = 4
    db_session.commit()

    sniper = make_sniper([FakeResponse(200, course_detail_html)])
    summary = sniper.recheck_delisted_courses()

    db_session.refresh(course)
    assert summary.sections_relisted == 1
    assert course.is_listed is True
    assert course.delisted_at is None
    assert course.section_gone_streak == 0
    assert course.seats_capacity == 27, "and its seat data is live again"


def test_recheck_tier_leaves_a_still_missing_section_delisted(
    db_session, no_sleep, fast_pacer, section_gone_html, sent_emails
):
    course = seed_tracks(db_session, 1)[0]
    course.is_listed = False
    course.delisted_at = sniper_module.datetime.now()
    db_session.commit()

    sniper = make_sniper([FakeResponse(200, section_gone_html)])
    summary = sniper.recheck_delisted_courses()

    db_session.refresh(course)
    assert summary.sections_relisted == 0
    assert course.is_listed is False
    assert sent_emails == [], "rechecking must not re-notify"


def test_recheck_tier_is_rate_limited_by_its_interval(monkeypatch):
    monkeypatch.setattr(settings, "SNIPER_DELISTED_RECHECK_SECONDS", 3600)

    assert runtime_state.due_for_delisted_recheck(0.0) is True
    assert runtime_state.due_for_delisted_recheck(1800.0) is False
    assert runtime_state.due_for_delisted_recheck(3600.0) is True


# --- Cancellation notifications -------------------------------------------

def test_section_cancelled_notification_fires_once_per_user_per_course(
    db_session, no_sleep, fast_pacer, monkeypatch, section_gone_html
):
    monkeypatch.setattr(settings, "SNIPER_SECTION_GONE_THRESHOLD", 1)
    sent = []
    monkeypatch.setattr(
        "workers.notifier.send_email_notification",
        lambda to, subject, html: (sent.append((to, subject)), (True, None))[1],
    )

    seed_tracks(db_session, 1, users=2)
    gone = FakeResponse(200, section_gone_html)

    sniper = make_sniper([gone])
    sniper.run_queue_segment(max_courses=1)

    assert len(sent) == 2, "both trackers hear about it once"
    assert {to for to, _ in sent} == {"student0@purdue.edu", "student1@purdue.edu"}
    assert all("No Longer Offered" in subject for _, subject in sent)

    logs = db_session.query(models.NotificationLog).filter_by(
        notification_type="section_cancelled"
    ).all()
    assert len(logs) == 2
    assert all(log.status == "sent" for log in logs)

    # Every later recheck must stay silent.
    for _ in range(3):
        again = make_sniper([gone])
        again.recheck_delisted_courses()

    assert len(sent) == 2, "no re-notifying on subsequent sweeps"


def test_a_failed_cancellation_email_is_retried(
    db_session, no_sleep, fast_pacer, monkeypatch, section_gone_html
):
    """Only a *sent* log suppresses a retry, so a delivery outage is not silent."""
    monkeypatch.setattr(settings, "SNIPER_SECTION_GONE_THRESHOLD", 1)
    attempts = []
    outcome = {"ok": False}

    def fake_send(to, subject, html):
        attempts.append(to)
        return (True, None) if outcome["ok"] else (False, "resend down")

    monkeypatch.setattr("workers.notifier.send_email_notification", fake_send)

    course = seed_tracks(db_session, 1)[0]
    gone = FakeResponse(200, section_gone_html)

    make_sniper([gone]).run_queue_segment(max_courses=1)
    assert len(attempts) == 1

    outcome["ok"] = True
    track = db_session.query(models.Track).filter_by(course_id=course.id).one()
    retry = make_sniper([])
    assert retry.notify_section_cancelled(track) is True
    assert len(attempts) == 2

    assert retry.notify_section_cancelled(track) is False
    assert len(attempts) == 2


def test_seat_open_notification_still_fires(
    db_session, no_sleep, fast_pacer, monkeypatch, course_detail_html
):
    """The cancellation branch must not disturb the seat alerts that matter."""
    sent = []
    monkeypatch.setattr(
        "workers.notifier.send_email_notification",
        lambda to, subject, html: (sent.append(subject), (True, None))[1],
    )

    seed_tracks(db_session, 1)
    track = db_session.query(models.Track).one()
    track.notify_on_open = True
    db_session.commit()

    # Flip the fixture's Remaining cell from 0 to 4, which is a seat opening.
    html = course_detail_html.replace(
        '<td CLASS="dddefault">27</td>\n<td CLASS="dddefault">27</td>\n<td CLASS="dddefault">0</td>',
        '<td CLASS="dddefault">27</td>\n<td CLASS="dddefault">23</td>\n<td CLASS="dddefault">4</td>',
    )
    assert html != course_detail_html, "fixture markup changed; update this rewrite"
    sniper = make_sniper([FakeResponse(200, html)])
    summary = sniper.run_queue_segment(max_courses=1)

    assert summary.notifications_sent == 1
    assert any("SEAT OPEN" in subject for subject in sent)


# --- Observability --------------------------------------------------------

def test_dead_segment_logs_at_critical_with_the_dominant_reason(
    db_session, no_sleep, fast_pacer, monkeypatch, caplog
):
    """`Courses checked: 0/469` must never again read as a normal cycle."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 100)
    seed_tracks(db_session, 6)

    blocked = FakeResponse(200, "too many requests")
    sniper = make_sniper([blocked] * 6)

    with caplog.at_level("INFO", logger="workers.sniper"):
        summary = sniper.run_queue_segment(max_courses=6)

    assert summary.checked == 0
    assert summary.dominant_failure is CheckStatus.BLOCKED

    critical = [r for r in caplog.records if r.levelname == "CRITICAL"]
    assert critical, "a dead segment must escalate above INFO"
    assert "SNIPER NOT FUNCTIONING" in critical[0].getMessage()
    assert "blocked" in critical[0].getMessage()


def test_healthy_segment_does_not_log_above_info(
    db_session, no_sleep, fast_pacer, caplog, course_detail_html
):
    seed_tracks(db_session, 3)

    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 3)
    with caplog.at_level("INFO", logger="workers.sniper"):
        summary = sniper.run_queue_segment(max_courses=3)

    assert summary.checked == 3
    assert not [r for r in caplog.records if r.levelno > 20]


def test_empty_track_list_is_not_reported_as_a_failure(db_session, no_sleep, caplog):
    sniper = make_sniper([])
    with caplog.at_level("INFO", logger="workers.sniper"):
        summary = sniper.run_queue_segment(max_courses=5)

    assert summary.total_courses == 0
    assert summary.attempted == 0
    assert not [r for r in caplog.records if r.levelno > 20]


def test_sweep_completion_is_reported_once_per_full_pass(
    db_session, no_sleep, fast_pacer, caplog, course_detail_html
):
    seed_tracks(db_session, 4)
    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 9)

    with caplog.at_level("INFO", logger="workers.sniper"):
        sniper.run_queue_segment(max_courses=9)

    sweeps = [r for r in caplog.records if "Full sweep complete" in r.getMessage()]
    assert len(sweeps) == 2, "nine checks over four courses is two full sweeps"
    assert runtime_state.last_sweep_seconds is not None


def test_staleness_percentiles_report_the_user_visible_number(
    db_session, no_sleep, fast_pacer, course_detail_html
):
    courses = seed_tracks(db_session, 4)
    now = sniper_module.datetime.now()
    for course, minutes in zip(courses, (1, 5, 10, 40)):
        course.last_checked = now - sniper_module.timedelta(minutes=minutes)
    db_session.commit()

    stats = make_sniper([]).staleness_percentiles()

    assert stats["courses"] == 4
    assert stats["never_checked"] == 0
    assert stats["p50_seconds"] == pytest.approx(7.5 * 60, abs=5)
    assert stats["max_seconds"] == pytest.approx(40 * 60, abs=5)


def test_staleness_counts_courses_that_have_never_been_checked(
    db_session, no_sleep, fast_pacer
):
    """CRN 24805 had never been successfully checked at all."""
    seed_tracks(db_session, 3)

    stats = make_sniper([]).staleness_percentiles()

    assert stats["courses"] == 3
    assert stats["never_checked"] == 3
    assert "p50_seconds" not in stats
