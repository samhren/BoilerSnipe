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
from app.database import SessionLocal
from app import models
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
            subjects=["AAE", "AAS", "ABE", "AD", "AFT", "AGEC", "AGR", "AGRY", "AMST", "ANSC", "ANTH", "ARAB", "ARCH", "ASAM", "ASEC", "ASL", "ASM", "ASTR", "AT", "BAND", "BCHM", "BIOL", "BME", "BMS", "BTNY", "CAND", "CDIS", "CE", "CEM", "CGT", "CHE", "CHM", "CHNS", "CIT", "CLCS", "CLPH", "CM", "CMGT", "CMPL", "CNIT", "COM", "CPB", "CS", "CSCI", "CSR", "DANC", "DCTC", "EAPS", "ECE", "ECET", "ECON", "EDCI", "EDPS", "EDST", "EEE", "ENE", "ENGL", "ENGR", "ENGT", "ENTM", "ENTR", "EPCS", "EXPL", "FLM", "FMGT", "FNR", "FR", "FS", "GEOL", "GEP", "GER", "GRAD", "GREK", "GS", "GSLA", "HDFS", "HEBR", "HER", "HETM", "HHS", "HIST", "HK", "HONR", "HORT", "HSCI", "HSOP", "HTM", "IDE", "IDIS", "IE", "IET", "ILS", "IMPH", "INFO", "INT", "ITAL", "JPNS", "KOR", "LA", "LALS", "LATN", "LC", "LING", "MA", "MATH", "MCMP", "ME", "MET", "MFET", "MGMT", "MIL", "MSE", "MSL", "MSPE", "MUS", "NRES", "NS", "NUCL", "NUR", "NUTR", "OBHR", "OLS", "PES", "PHIL", "PHPR", "PHRM", "PHSC", "PHST", "PHYS", "POL", "PSY", "PTGS", "PUBH", "REG", "REL", "RPMP", "RUSS", "SCI", "SCLA", "SFS", "SLHS", "SOC", "SPAN", "STAT", "SYS", "TCM", "TDM", "TECH", "THTR", "TLI", "VCS", "VIP", "VM", "WGSS"]
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


def run_startup_scrape():
    """Clear database and run initial scrape on startup"""
    print("\n[STARTUP] Preparing for initial scrape...", flush=True)
    db = SessionLocal()
    try:
        # Check if tables exist
        if hasattr(models, 'Course'):
            print("[STARTUP] Clearing existing course data...", flush=True)
            # Delete all courses (cascade will handle tracks if configured, or we can be explicit)
            db.query(models.Course).delete()
            db.commit()
            print("[STARTUP] Database cleared.", flush=True)
            
            print("[STARTUP] Starting fresh inventory scrape...", flush=True)
            job_inventory_scraper()
            print("[STARTUP] Initial scrape completed successfully.", flush=True)
    except Exception as e:
        print(f"Warning: Startup scrape failed: {e}", flush=True)
    finally:
        db.close()


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
    
    # Run startup scrape (Clear DB + Scrape)
    run_startup_scrape()

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
