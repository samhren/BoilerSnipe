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
from .inventory_scraper import run_inventory_scraper
from .sniper import run_sniper


def job_inventory_scraper():
    """Wrapper for inventory scraper job"""
    print(f"\n{'='*60}")
    print(f"INVENTORY SCRAPER JOB - {datetime.now()}")
    print(f"{'='*60}\n")

    try:
        # Configure which terms and subjects to scrape
        # You can customize this based on your needs
        run_inventory_scraper(
            term_code="202620",  # Spring 2026
            term_name="Spring 2026",
            subjects=["MA", "CS", "ECON", "STAT", "PHYS", "CHEM"]
        )
    except Exception as e:
        print(f"Error in inventory scraper job: {str(e)}")


def job_seat_sniper():
    """Wrapper for seat sniper job"""
    print(f"\n{'='*60}")
    print(f"SEAT SNIPER JOB - {datetime.now()}")
    print(f"{'='*60}\n")

    try:
        run_sniper()
    except Exception as e:
        print(f"Error in seat sniper job: {str(e)}")


def start_scheduler():
    """Start the background job scheduler"""
    scheduler = BlockingScheduler()

    # Add Inventory Scraper job (runs daily at 2 AM by default)
    # Parses INVENTORY_CRON from settings (e.g., "0 2 * * *")
    scheduler.add_job(
        job_inventory_scraper,
        trigger=CronTrigger.from_crontab(settings.INVENTORY_CRON),
        id='inventory_scraper',
        name='Daily Inventory Scraper',
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
    print(f"  1. Inventory Scraper: {settings.INVENTORY_CRON} (Daily at 2 AM)")
    print(f"  2. Seat Sniper: Every {settings.SNIPER_INTERVAL_MINUTES} minutes")
    print(f"\nScheduler started at {datetime.now()}")
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
