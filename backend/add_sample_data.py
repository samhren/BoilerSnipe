"""
Add sample course data for testing
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Course

def add_sample_courses():
    db = SessionLocal()

    sample_courses = [
        {
            "crn": "12345",
            "course_code": "CS 18000",
            "title": "Problem Solving And Object-Oriented Programming",
            "instructor": "Dr. Smith",
            "time": "10:30 am - 11:20 am",
            "days": "MWF",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 30,
            "seats_available": 30,
            "seats_remaining": 0
        },
        {
            "crn": "22126",
            "course_code": "MA 35100",
            "title": "Elementary Linear Algebra",
            "instructor": "Prof. Chen",
            "time": "1:30 pm - 2:20 pm",
            "days": "TR",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 40,
            "seats_available": 38,
            "seats_remaining": 2
        },
        {
            "crn": "33567",
            "course_code": "CS 25100",
            "title": "Data Structures And Algorithms",
            "instructor": "Dr. Johnson",
            "time": "9:00 am - 10:15 am",
            "days": "MW",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 50,
            "seats_available": 50,
            "seats_remaining": 0
        },
        {
            "crn": "44890",
            "course_code": "MA 26100",
            "title": "Multivariate Calculus",
            "instructor": "Prof. Williams",
            "time": "12:00 pm - 1:15 pm",
            "days": "TR",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 35,
            "seats_available": 32,
            "seats_remaining": 3
        },
        {
            "crn": "55123",
            "course_code": "ECON 25100",
            "title": "Microeconomics",
            "instructor": "Dr. Anderson",
            "time": "2:30 pm - 3:45 pm",
            "days": "MW",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 45,
            "seats_available": 45,
            "seats_remaining": 0
        },
        {
            "crn": "66234",
            "course_code": "CS 38100",
            "title": "Introduction to Database Systems",
            "instructor": "Dr. Martinez",
            "time": "4:30 pm - 5:45 pm",
            "days": "TR",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 25,
            "seats_available": 20,
            "seats_remaining": 5
        },
        {
            "crn": "77345",
            "course_code": "STAT 35000",
            "title": "Introduction to Statistics",
            "instructor": "Prof. Taylor",
            "time": "8:00 am - 9:15 am",
            "days": "MW",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 60,
            "seats_available": 60,
            "seats_remaining": 0
        },
        {
            "crn": "88456",
            "course_code": "CS 25200",
            "title": "Systems Programming",
            "instructor": "Dr. Brown",
            "time": "3:00 pm - 4:15 pm",
            "days": "TR",
            "term_code": "202620",
            "term_name": "Spring 2026",
            "seats_capacity": 30,
            "seats_available": 28,
            "seats_remaining": 2
        }
    ]

    try:
        for course_data in sample_courses:
            # Check if course already exists
            existing = db.query(Course).filter(Course.crn == course_data["crn"]).first()
            if not existing:
                course = Course(**course_data)
                db.add(course)
                print(f"✓ Added: {course_data['course_code']} - {course_data['title']}")
            else:
                print(f"- Skipped: {course_data['course_code']} (already exists)")

        db.commit()
        print(f"\n✅ Successfully added {len(sample_courses)} sample courses!")
        print("You can now search and track these courses in the app.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Adding sample course data to database...\n")
    add_sample_courses()
