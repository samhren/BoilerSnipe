import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import User, Course, Track
from fastapi import HTTPException
from app.schemas import TrackCreate
from app import main

from starlette.requests import Request

# Mock request and dependency
def create_mock_request():
    return Request(scope={
        "type": "http", 
        "client": ("127.0.0.1", 8000), 
        "headers": [],
        "path": "/api/tracks",
        "method": "POST"
    })

def verify_limit():
    db = SessionLocal()
    test_email = "limit_test_user@example.com"
    
    try:
        # 1. Cleanup previous test run
        user = db.query(User).filter(User.email == test_email).first()
        if user:
            # Delete tracks first
            db.query(Track).filter(Track.user_id == user.id).delete()
            db.delete(user)
            db.commit()
            print("Cleaned up previous test user.")

        # 2. Create test user
        user = User(email=test_email, hashed_password="hashed_password")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created test user: {user.email}")

        # 3. Ensure we have at least 11 courses to track
        # We'll create dummy courses if needed
        courses = db.query(Course).limit(11).all()
        if len(courses) < 11:
            print(f"Not enough courses in DB ({len(courses)}), creating dummies...")
            for i in range(11 - len(courses)):
                dummy = Course(
                    crn=f"DUMMY{i}",
                    course_code=f"DUMMY {i}",
                    title=f"Dummy Course {i}",
                    term_code="202620",
                    seats_capacity=10,
                    seats_available=5,
                    seats_remaining=5
                )
                db.add(dummy)
            db.commit()
            courses = db.query(Course).limit(11).all()
        
        print(f"Found/Created {len(courses)} courses for testing.")

        # 4. Add 10 tracks
        print("Adding 10 tracks...")
        for i in range(10):
            course = courses[i]
            # specific logic to call create_track without full HTTP stack or use direct DB
            # Using direct DB to simulate pre-existing valid state
            track = Track(
                user_id=user.id,
                course_id=course.id,
                notify_on_open=True,
                notify_on_close=True,
                last_status="open",
                last_seats=1
            )
            db.add(track)
        db.commit()
        
        count = db.query(Track).filter(Track.user_id == user.id, Track.is_active == True).count()
        print(f"User now has {count} active tracks.")
        assert count == 10

        # 5. Try to add the 11th track via the API function logic
        # We need to simulate the API call. Since create_track is a fastapi endpoint, 
        # calling it directly requires mocking dependencies.
        # Alternatively, we can extract the logic or just verify the direct DB check?
        # The logic is IN the create_track function. So we should call it.
        
        print("Attempting to add 11th track (should fail)...")
        course_11 = courses[10]
        track_data = TrackCreate(
            crn=course_11.crn,
            notify_on_open=True,
            notify_on_close=True
        )
        
        try:
            main.create_track(
                request=create_mock_request(),
                track_data=track_data,
                current_user=user,
                db=db
            )
            print("❌ FAILED: API allowed creating 11th track!")
        except HTTPException as e:
            if e.status_code == 400 and "only track up to 10 courses" in e.detail:
                print("✅ SUCCESS: API blocked 11th track with correct error.")
            else:
                print(f"❌ FAILED: API raised unexpected exception: {e}")
        except Exception as e:
            print(f"❌ FAILED: Unexpected error: {e}")

    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        # Cleanup
        if user:
             db.query(Track).filter(Track.user_id == user.id).delete()
             db.delete(user)
             db.commit()
             print("Cleanup complete.")
        db.close()

if __name__ == "__main__":
    verify_limit()
