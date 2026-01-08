
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.database import SessionLocal
from app.models import Course
from workers.sniper import SeatSniper

# Mock CRN that we know exists and is not currently tracked by anyone (or we can use one that is)
# Ideally one that has data. Let's pick a random one or use one from the DB.
TEST_CRN = "21683" # Example CRN, we might need to find a real one first.

def verify_stale_fix():
    db = SessionLocal()
    try:
        # 1. Create a dummy course for testing if not exists
        course = db.query(Course).filter(Course.crn == TEST_CRN).first()
        if not course:
            course = Course(
                crn=TEST_CRN,
                course_code="TEST 101",
                title="Test Course",
                term_code="202620",
                created_at=datetime.now()
            )
            db.add(course)
            db.commit()
            db.refresh(course)

        print(f"Testing with Course: {course.course_code} (CRN: {course.crn})")
        
        # 2. Manually make it stale (set last_checked to 1 hour ago)
        old_time = datetime.now(course.created_at.tzinfo if course.created_at else None) - timedelta(hours=1)
        course.last_checked = old_time
        db.commit()
        print(f"Set last_checked to: {course.last_checked} (Stale)")

        # Mock SeatSniper to avoid network calls and dependency on real CRNs
        original_check = SeatSniper.check_seat_availability
        
        def mock_check(self, crn, term_code):
            print(f"MOCK SNIPER: Checking seats for {crn}...")
            return {
                'seats_capacity': 100,
                'seats_available': 50,
                'seats_remaining': 50,
                'last_checked': datetime.now()
            }
            
        SeatSniper.check_seat_availability = mock_check

        print("Verifying stale check logic...")
        
        # Logic from main.py
        is_stale = False
        if not course.last_checked:
            is_stale = True
        else:
             # Check if older than 15 minutes
            now = datetime.now(course.last_checked.tzinfo)
            time_diff = now - course.last_checked
            if time_diff.total_seconds() > 900:
                is_stale = True
        
        print(f"Is Stale? {is_stale}")
        if not is_stale:
            print("FAIL: Course should be stale but wasn't detected as such.")
            return

        # 4. If stale, run sniper (simulating main.py)
        if is_stale:
            print("Triggering refresh...")
            sniper = SeatSniper()
            seat_data = sniper.check_seat_availability(course.crn, course.term_code)
            if seat_data:
                print("Fresh data retrieved!")
                print(seat_data)
                
                # Update course
                course.seats_capacity = seat_data['seats_capacity']
                course.seats_available = seat_data['seats_available']
                course.seats_remaining = seat_data['seats_remaining']
                course.last_checked = seat_data['last_checked']
                db.commit()
            else:
                print("Failed to get seat data from sniper.")
                
        # 5. Verify it's no longer stale
        db.refresh(course)
        print(f"New last_checked: {course.last_checked}")
        
        # Re-check staleness
        is_stale_again = False
        time_diff = datetime.now(course.last_checked.tzinfo) - course.last_checked
        if time_diff.total_seconds() > 900:
            is_stale_again = True
            
        if is_stale_again:
             print("FAIL: Course is still stale after refresh.")
        else:
             print("SUCCESS: Course successfully refreshed!")
             
        # Cleanup
        SeatSniper.check_seat_availability = original_check


    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_stale_fix()
