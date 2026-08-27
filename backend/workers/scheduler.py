"""
Background job scheduler for running workers
"""

import logging
import sys
import threading
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.database import init_db
from app.migrate import migrate
from .inventory_scraper import run_inventory_scraper
from .sniper import run_sniper_forever


def job_inventory_scraper():
    """Wrapper for inventory scraper job"""
    print(f"\n{'='*60}")
    print(f"INVENTORY SCRAPER JOB - {datetime.now()}")
    print(f"{'='*60}\n")

    try:
        return run_inventory_scraper(
            term_code=settings.CURRENT_TERM_CODE,
            term_name=settings.CURRENT_TERM_NAME,
            subjects=settings.inventory_subject_list
        )
    except Exception as e:
        print(f"Error in inventory scraper job: {str(e)}")
        return 0


def start_seat_sniper(stop_event: threading.Event) -> threading.Thread:
    """Run the seat sniper as a continuous background walk.

    The sniper is no longer a scheduled job. A full sweep of the tracked-course
    queue takes as long as the pacer allows - roughly ten minutes at the
    measured ceiling - which no fixed trigger interval can express without
    either overlapping cycles or truncating the sweep. It runs in a thread so
    the blocking scheduler can still own the inventory cron.
    """
    thread = threading.Thread(
        target=run_sniper_forever,
        kwargs={"stop_event": stop_event},
        name="seat-sniper",
        daemon=True,
    )
    thread.start()
    return thread


def run_startup_scrape_once():
    """Run one current-term inventory scrape during this worker startup."""
    if not settings.RUN_STARTUP_INVENTORY_ONCE:
        print("[STARTUP] One-time inventory scrape disabled.", flush=True)
        return

    print("\n[STARTUP] Preparing for initial update scrape...", flush=True)
    try:
        print(f"[STARTUP] Starting one-time inventory update for {settings.CURRENT_TERM_NAME}...", flush=True)
        scraped_count = job_inventory_scraper()
        if scraped_count <= 0:
            print("[STARTUP] Inventory scrape returned no courses; will retry on next worker start.", flush=True)
            return

        print(f"[STARTUP] Initial update completed successfully. Scraped {scraped_count} course sections.", flush=True)
    except Exception as e:
        print(f"Warning: Startup scrape failed: {e}", flush=True)


def configure_logging():
    """Send worker logs to stdout.

    The sniper reports blocks, breaker trips and dead cycles through the
    `logging` module. Without this the root logger defaults to WARNING with no
    handler, and those lines would be exactly as invisible as the bare
    "Failed to check seats" prints they replaced.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )


def start_scheduler():
    """Start the background job scheduler"""
    configure_logging()
    init_db()
    migrate()

    scheduler = BlockingScheduler()

    if settings.ENABLE_RECURRING_INVENTORY:
        scheduler.add_job(
            job_inventory_scraper,
            trigger=CronTrigger.from_crontab(settings.INVENTORY_CRON),
            id='inventory_scraper',
            name='Inventory Scraper',
            replace_existing=True
        )

    print("="*60)
    print("BOILERSNIPE - BACKGROUND SCHEDULER")
    print("="*60)
    print(f"\nScheduled Jobs:")
    print(f"  1. Startup Inventory Scraper: {'Enabled' if settings.RUN_STARTUP_INVENTORY_ONCE else 'Disabled'}")
    print(f"  2. Recurring Inventory Scraper: {settings.INVENTORY_CRON if settings.ENABLE_RECURRING_INVENTORY else 'Disabled'}")
    print(f"  3. Seat Sniper: Continuous, paced at {settings.SNIPER_PACER_START_RATE} req/s "
          f"(adaptive {settings.SNIPER_PACER_MIN_RATE}-{settings.SNIPER_PACER_MAX_RATE}), "
          f"queue refresh every {settings.SNIPER_COURSE_REFRESH_SECONDS}s")
    print(f"\nScheduler started at {datetime.now()}")

    run_startup_scrape_once()

    print("="*60)
    print("\nPress Ctrl+C to stop\n")

    # Started after the startup scrape so the sniper walks a populated
    # inventory rather than racing it.
    sniper_stop = threading.Event()
    start_seat_sniper(sniper_stop)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\nShutting down scheduler...")
        sniper_stop.set()
        scheduler.shutdown()
        print("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
