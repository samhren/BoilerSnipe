from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from .database import get_db, init_db
from . import models, schemas, auth
from .config import settings

app = FastAPI(
    title="BoilerSnipe API",
    description="Track Purdue course seat availability and get notified instantly",
    version="1.0.0"
)

# CORS middleware
origins = ["http://localhost:5173", "http://localhost:3000"]
if settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


# Authentication Endpoints
@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    new_user = models.User(
        email=user_data.email,
        telegram_chat_id=user_data.telegram_chat_id,
        hashed_password=models.User.hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.post("/api/auth/login", response_model=schemas.Token)
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token"""
    user = auth.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user information"""
    return current_user


# Course Endpoints
@app.get("/api/courses", response_model=List[schemas.CourseResponse])
def search_courses(
    query: str = "",
    term_code: str = None,
    db: Session = Depends(get_db)
):
    """Search courses in the database"""
    courses_query = db.query(models.Course)

    if term_code:
        courses_query = courses_query.filter(models.Course.term_code == term_code)

    if query:
        search_filter = f"%{query}%"
        courses_query = courses_query.filter(
            (models.Course.course_code.ilike(search_filter)) |
            (models.Course.title.ilike(search_filter)) |
            (models.Course.crn.ilike(search_filter))
        )

    courses = courses_query.order_by(models.Course.course_code).limit(50).all()
    return courses


@app.get("/api/courses/{crn}", response_model=schemas.CourseResponse)
def get_course_by_crn(crn: str, db: Session = Depends(get_db)):
    """Get a specific course by CRN"""
    course = db.query(models.Course).filter(models.Course.crn == crn).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# Track Endpoints
@app.post("/api/tracks", response_model=schemas.TrackResponse, status_code=status.HTTP_201_CREATED)
def create_track(
    track_data: schemas.TrackCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Track a course by CRN"""
    # Find the course
    course = db.query(models.Course).filter(models.Course.crn == track_data.crn).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found. Course may need to be added to inventory first.")

    # Check if already tracking
    existing_track = db.query(models.Track).filter(
        models.Track.user_id == current_user.id,
        models.Track.course_id == course.id
    ).first()

    if existing_track:
        if not existing_track.is_active:
            existing_track.is_active = True
            db.commit()
            db.refresh(existing_track)
            return existing_track
        raise HTTPException(status_code=400, detail="Already tracking this course")

    # Create new track
    new_track = models.Track(
        user_id=current_user.id,
        course_id=course.id,
        notify_on_open=track_data.notify_on_open,
        notify_on_close=track_data.notify_on_close,
        last_status="closed",
        last_seats=course.seats_remaining
    )
    db.add(new_track)
    db.commit()
    db.refresh(new_track)

    # If course hasn't been checked yet (0/0), trigger immediate seat check
    if course.seats_capacity == 0 and course.seats_remaining == 0:
        try:
            from workers.sniper import SeatSniper
            sniper = SeatSniper()
            seat_data = sniper.check_seat_availability(course.crn, course.term_code)
            if seat_data:
                # Update directly in our session
                course.seats_capacity = seat_data['seats_capacity']
                course.seats_available = seat_data['seats_available']
                course.seats_remaining = seat_data['seats_remaining']
                course.last_checked = seat_data['last_checked']
                db.commit()
            sniper.close()
            db.refresh(course)
            db.refresh(new_track)
        except Exception as e:
            print(f"Failed to check seats for new track: {e}")

    return new_track


@app.get("/api/tracks", response_model=List[schemas.TrackResponse])
def get_my_tracks(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tracks for current user"""
    tracks = db.query(models.Track).filter(
        models.Track.user_id == current_user.id,
        models.Track.is_active == True
    ).all()
    return tracks


@app.patch("/api/tracks/{track_id}", response_model=schemas.TrackResponse)
def update_track(
    track_id: int,
    track_update: schemas.TrackUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update track settings"""
    track = db.query(models.Track).filter(
        models.Track.id == track_id,
        models.Track.user_id == current_user.id
    ).first()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Update fields
    if track_update.notify_on_open is not None:
        track.notify_on_open = track_update.notify_on_open
    if track_update.notify_on_close is not None:
        track.notify_on_close = track_update.notify_on_close
    if track_update.is_active is not None:
        track.is_active = track_update.is_active

    db.commit()
    db.refresh(track)
    return track


@app.delete("/api/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_track(
    track_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a track (stop tracking a course)"""
    track = db.query(models.Track).filter(
        models.Track.id == track_id,
        models.Track.user_id == current_user.id
    ).first()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    db.delete(track)
    db.commit()
    return None


# Health check
@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "boilersnipe"}
