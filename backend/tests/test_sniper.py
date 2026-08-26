"""Tests for the seat sniper's rate-limit resilience.

Every HTTP call is mocked. These tests exist because the 2026-08-25 outage was
invisible: Purdue returned HTTP 200 block pages for 24 hours and the sniper
reported them the same way it reports a parse miss.
"""

import itertools

import pytest
import requests
from bs4 import BeautifulSoup

from app import models
from app.config import settings
from workers import sniper as sniper_module
from workers.sniper import (
    CheckStatus,
    SeatSniper,
    looks_like_block_page,
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
    """Pacing is real in production, but tests should not actually wait."""
    slept = []
    monkeypatch.setattr(sniper_module.time, "sleep", slept.append)
    return slept


def make_sniper(responses):
    sniper = SeatSniper()
    sniper.session = FakeSession(responses)
    return sniper


def seed_tracks(session, count, term_code=None):
    """Create `count` distinct tracked courses in the current term."""
    term_code = term_code or settings.CURRENT_TERM_CODE
    user = models.User(email="student@purdue.edu", hashed_password="x")
    session.add(user)
    session.flush()

    for i in range(count):
        course = models.Course(
            crn=f"{10000 + i}",
            course_code=f"CS {10000 + i}",
            title=f"Course {i}",
            term_code=term_code,
            is_listed=True,
            seats_capacity=27,
            seats_available=27,
            seats_remaining=0,
        )
        session.add(course)
        session.flush()
        session.add(models.Track(
            user_id=user.id,
            course_id=course.id,
            is_active=True,
            notify_on_open=False,
            notify_on_close=False,
            last_seats=0,
        ))
    session.commit()


# --- Outcome classification ----------------------------------------------

def test_block_page_on_200_is_classified_blocked(db_session, block_page_html):
    """The exact failure that caused the outage: a 200 that is really a block."""
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


# --- Block-page sniffing --------------------------------------------------

def test_looks_like_block_page_matches_case_insensitively(block_page_html):
    assert looks_like_block_page(block_page_html)
    assert looks_like_block_page(block_page_html.upper())


def test_looks_like_block_page_ignores_full_size_pages(course_detail_html):
    """The length ceiling keeps a real page from ever matching by accident."""
    assert not looks_like_block_page(course_detail_html)
    assert not looks_like_block_page(course_detail_html + "too many requests")
    assert not looks_like_block_page("")


# --- Circuit breaker ------------------------------------------------------

def test_breaker_aborts_cycle_after_consecutive_failures(db_session, no_sleep, monkeypatch):
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 5)
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 20)

    blocked = FakeResponse(200, "too many requests")
    sniper = make_sniper([blocked] * 20)
    summary = sniper.run_check_cycle()

    assert summary.breaker_tripped
    assert summary.attempted == 5, "must stop at the threshold, not grind all 20"
    assert summary.unchecked_after_abort == 15
    assert summary.checked == 0
    assert len(sniper.session.calls) == 5


def test_breaker_resets_on_an_interleaved_success(db_session, no_sleep, monkeypatch, course_detail_html):
    """Only *consecutive* failures trip the breaker."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 6)

    blocked = FakeResponse(200, "too many requests")
    ok = FakeResponse(200, course_detail_html)
    # fail, fail, ok, fail, fail, ok - never three in a row
    sniper = make_sniper([blocked, blocked, ok, blocked, blocked, ok])
    summary = sniper.run_check_cycle()

    assert not summary.breaker_tripped
    assert summary.attempted == 6
    assert summary.checked == 2


def test_parse_failures_alone_do_not_trip_the_breaker(db_session, no_sleep, monkeypatch):
    """A parser bug is not a reason to stop talking to Purdue."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 5)

    page = "<html><body>" + ("<p>x</p>" * 500) + "</body></html>"
    sniper = make_sniper([FakeResponse(200, page)] * 5)
    summary = sniper.run_check_cycle()

    assert not summary.breaker_tripped
    assert summary.attempted == 5
    assert summary.status_counts[CheckStatus.PARSE_FAILED] == 5


# --- Backoff across cycles ------------------------------------------------

def test_backoff_persists_across_cycles_and_clears_after_success(
    db_session, no_sleep, monkeypatch, course_detail_html
):
    """The core regression: a fresh SeatSniper per cycle must still be suppressed."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 3)
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 10)

    blocked = FakeResponse(200, "too many requests")

    # Cycle 1: trips the breaker and arms backoff.
    first = make_sniper([blocked] * 3)
    summary_one = first.run_check_cycle()
    assert summary_one.breaker_tripped
    assert runtime_state.backoff_level == 1
    assert runtime_state.backoff_remaining_seconds() > 0

    # Cycle 2: a brand new instance, and it must not touch Purdue at all.
    second = make_sniper([])
    summary_two = second.run_check_cycle()
    assert summary_two.skipped_for_backoff
    assert summary_two.attempted == 0
    assert second.session.calls == []

    # Once backoff expires, the first success clears it.
    runtime_state.backoff_until = None
    third = make_sniper([FakeResponse(200, course_detail_html)] * 10)
    summary_three = third.run_check_cycle()

    assert not summary_three.skipped_for_backoff
    assert summary_three.checked == 10
    assert runtime_state.backoff_level == 0
    assert runtime_state.backoff_remaining_seconds() == 0
    assert runtime_state.last_success_at is not None


def test_backoff_escalates_and_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "SNIPER_BACKOFF_MAX_MINUTES", 60)

    delays = [runtime_state.trip_backoff() for _ in range(8)]

    # Exponential from a 5 minute base, with +/-20% jitter, capped at 60.
    assert 4.0 <= delays[0] <= 6.0
    assert 8.0 <= delays[1] <= 12.0
    assert all(d <= 60 for d in delays)
    assert delays[-1] > 40
    assert runtime_state.backoff_level == 8


# --- Request budget and rotation -----------------------------------------

def test_budget_caps_a_cycle_and_rotates_the_starting_point(
    db_session, no_sleep, monkeypatch, course_detail_html
):
    """A growing course list must not starve the same tail every cycle."""
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 4)
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 5)
    seed_tracks(db_session, 10)

    ok = FakeResponse(200, course_detail_html)

    first = make_sniper([ok] * 4)
    summary_one = first.run_check_cycle()
    assert summary_one.attempted == 4
    assert summary_one.skipped_for_budget == 6

    second = make_sniper([ok] * 4)
    summary_two = second.run_check_cycle()
    assert summary_two.attempted == 4

    crns_one = [url.split("crn_in=")[1] for url in first.session.calls]
    crns_two = [url.split("crn_in=")[1] for url in second.session.calls]
    assert crns_one != crns_two, "second cycle must start where the first stopped"
    assert not set(crns_one) & set(crns_two)


def test_pacing_delay_is_applied_between_requests(
    db_session, no_sleep, monkeypatch, course_detail_html
):
    monkeypatch.setattr(settings, "SNIPER_REQUEST_DELAY_SECONDS", 0.75)
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 4)

    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 4)
    sniper.run_check_cycle()

    # One delay between each pair of requests, none before the first.
    assert no_sleep == [0.75, 0.75, 0.75]


# --- Loud failure ---------------------------------------------------------

def test_dead_cycle_logs_at_critical_with_the_dominant_reason(
    db_session, no_sleep, monkeypatch, caplog
):
    """`Courses checked: 0/469` must never again read as a normal cycle."""
    monkeypatch.setattr(settings, "SNIPER_MAX_CONSECUTIVE_FAILURES", 100)
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 6)

    blocked = FakeResponse(200, "too many requests")
    sniper = make_sniper([blocked] * 6)

    with caplog.at_level("INFO", logger="workers.sniper"):
        summary = sniper.run_check_cycle()

    assert summary.checked == 0
    assert summary.dominant_failure is CheckStatus.BLOCKED

    critical = [r for r in caplog.records if r.levelname == "CRITICAL"]
    assert critical, "a dead cycle must escalate above INFO"
    assert "SNIPER NOT FUNCTIONING" in critical[0].getMessage()
    assert "blocked" in critical[0].getMessage()


def test_healthy_cycle_does_not_log_above_info(
    db_session, no_sleep, monkeypatch, caplog, course_detail_html
):
    monkeypatch.setattr(settings, "SNIPER_MAX_REQUESTS_PER_CYCLE", 100)
    seed_tracks(db_session, 3)

    sniper = make_sniper([FakeResponse(200, course_detail_html)] * 3)
    with caplog.at_level("INFO", logger="workers.sniper"):
        summary = sniper.run_check_cycle()

    assert summary.checked == 3
    assert not [r for r in caplog.records if r.levelno > 20]


def test_empty_track_list_is_not_reported_as_a_failure(db_session, no_sleep, caplog):
    sniper = make_sniper([])
    with caplog.at_level("INFO", logger="workers.sniper"):
        summary = sniper.run_check_cycle()

    assert summary.total_courses == 0
    assert not [r for r in caplog.records if r.levelno > 20]
