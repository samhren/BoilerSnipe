"""
Background job scheduler for running workers
"""

import sys
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.database import init_db
from app.migrate import migrate
from .inventory_scraper import run_inventory_scraper
from .sniper import run_sniper


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


def job_seat_sniper():
    """Wrapper for seat sniper job"""
    print(f"\n{'='*60}")
    print(f"SEAT SNIPER JOB - {datetime.now()}")
    print(f"{'='*60}\n")

    try:
        run_sniper()
    except Exception as e:
        print(f"Error in seat sniper job: {str(e)}")


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


def start_scheduler():
    """Start the background job scheduler"""
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

    # Add Seat Sniper job (runs every 5 minutes by default)
    scheduler.add_job(
        job_seat_sniper,
        trigger=IntervalTrigger(minutes=settings.SNIPER_INTERVAL_MINUTES),
        id='seat_sniper',
        name='Seat Availability Checker',
        replace_existing=True
    )

    print("="*60)
    print("BOILERSNIPE - BACKGROUND SCHEDULER")
    print("="*60)
    print(f"\nScheduled Jobs:")
    print(f"  1. Startup Inventory Scraper: {'Enabled' if settings.RUN_STARTUP_INVENTORY_ONCE else 'Disabled'}")
    print(f"  2. Recurring Inventory Scraper: {settings.INVENTORY_CRON if settings.ENABLE_RECURRING_INVENTORY else 'Disabled'}")
    print(f"  3. Seat Sniper: Every {settings.SNIPER_INTERVAL_MINUTES} minutes")
    print(f"\nScheduler started at {datetime.now()}")

    run_startup_scrape_once()

    print("="*60)
    print("\nPress Ctrl+C to stop\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\nShutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
