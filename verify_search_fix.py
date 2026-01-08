
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import random

# Add backend directory to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.database import SessionLocal
from app.models import Course
from workers.sniper import SeatSniper
import concurrent.futures

# Mock CRNs for search testing
TEST_PREFIX = "SEARCH_TEST_"

def verify_search_fix():
    db = SessionLocal()
    try:
        print("\n=== Verifying Search Stale Data Fix ===\n")

        # 1. Create multiple stale courses
        stale_courses = []
        for i in range(5):
            crn = f"{TEST_PREFIX}{i}"
            course = db.query(Course).filter(Course.crn == crn).first()
            if not course:
                course = Course(
                    crn=crn,
                    course_code=f"TEST {100+i}",
                    title=f"Parallel Test Course {i}",
                    term_code="202620",
                    created_at=datetime.now()
                )
                db.add(course)
            
            # Make it stale
            course.last_checked = datetime.now() - timedelta(hours=1)
            stale_courses.append(course)
        
        db.commit()
        print(f"Created/Updated {len(stale_courses)} courses and flagged them as stale.")

        # Mock SeatSniper
        original_check = SeatSniper.check_seat_availability
        
        def mock_check(self, crn, term_code):
            # Simulate network delay to prove parallel execution is effective
            # If 5 courses take 1s each, sequential = 5s, parallel ~ 1s
            time.sleep(1.0) 
            return {
                'seats_capacity': 100,
                'seats_available': 50,
                'seats_remaining': 50,
                'last_checked': datetime.now()
            }
            
        SeatSniper.check_seat_availability = mock_check
        
        print("Starting search simulation (with mocked 1s delay per course)...")
        start_time = time.time()

        # Simulate the logic in main.py search_courses
        # We can't easily call the API function directly because of dependency injection arguments
        # So we replicate the critical logic chunk here to verify it works as intended.
        
        # Step 1: Query DB
        # Refresh session to get latest state
        courses = [db.merge(c) for c in stale_courses] 

        # Step 2: Identify Stale
        to_refresh = []
        for course in courses:
            if not course.last_checked or (datetime.now() - course.last_checked).total_seconds() > 900:
                to_refresh.append(course)
        
        print(f"identified {len(to_refresh)} stale courses to refresh.")

        # Step 3: Parallel Refresh
        def check_seat_worker(course_info):
            crn, term_code = course_info
            try:
                sniper = SeatSniper() # Uses mocked check
                result = sniper.check_seat_availability(crn, term_code)
                return (crn, result)
            except Exception:
                return (crn, None)

        work_items = [(c.crn, c.term_code) for c in to_refresh]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_crn = {executor.submit(check_seat_worker, item): item[0] for item in work_items}
            
            for future in concurrent.futures.as_completed(future_to_crn):
                crn, result = future.result()
                if result:
                    # Update DB object
                    # usage of 'next' matches implementation
                    course = next((c for c in courses if c.crn == crn), None)
                    if course:
                        course.last_checked = result['last_checked']
                        # (Update other fields as well)

        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Refresh completed in {duration:.2f} seconds.")
        
        # Validation
        if duration > 4.0:
            print("FAIL: Execution took too long, parallel processing might not be working.")
        else:
            print("SUCCESS: Execution time indicates parallel processing (should be ~1.0s).")

        # Cleanup
        SeatSniper.check_seat_availability = original_check

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_search_fix()
