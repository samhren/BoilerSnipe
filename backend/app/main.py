from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta, datetime
import concurrent.futures
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .database import get_db, init_db
from . import models, schemas, auth
from .config import settings
from workers.notifier import send_welcome_email

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="BoilerSnipe API",
    description="Track Purdue course seat availability and get notified instantly",
    version="1.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



# Trusted Host middleware (must be added before CORS)
# Allow all hosts when behind a reverse proxy, or use ALLOWED_HOSTS for direct access
allowed_hosts = [host.strip() for host in settings.ALLOWED_HOSTS.split(",")]
if "*" not in allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )

# CORS middleware
origins = ["http://localhost:5173", "http://localhost:3000"]
if settings.FRONTEND_URL:
    # Strip trailing slash if present to ensure exact match with Origin header
    url = settings.FRONTEND_URL.rstrip("/")
    origins.append(url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print(f"DEBUG: ALLOWED_HOSTS={settings.ALLOWED_HOSTS}")
    print(f"DEBUG: FRONTEND_URL={settings.FRONTEND_URL}")
    print(f"DEBUG: CORS Origins={origins}")
    init_db()


# Authentication Endpoints
@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user_data: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    new_user = models.User(
        email=user_data.email,
        hashed_password=models.User.hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send welcome email
    background_tasks.add_task(send_welcome_email, user_data.email)

    return new_user


@app.post("/api/auth/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(request: Request, login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
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


@app.post("/api/auth/google", response_model=schemas.Token)
@limiter.limit("10/minute")
def google_login(request: Request, login_data: schemas.GoogleLoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Login with Google"""
    # Verify Google token
    id_info = auth.verify_google_token(login_data.token)
    if not id_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = id_info.get("email")
    google_id = id_info.get("sub")
    
    if not email:
        raise HTTPException(status_code=400, detail="Token does not contain email")

    # Check if user exists
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        # Create new user
        # We set a random password since they login with Google
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        random_password = ''.join(secrets.choice(alphabet) for i in range(20))
        
        user = models.User(
            email=email,
            google_id=google_id,
            hashed_password=models.User.hash_password(random_password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Send welcome email for new Google users
        background_tasks.add_task(send_welcome_email, email)
    else:
        # Link google_id if not linked
        if not user.google_id:
            user.google_id = google_id
            db.commit()

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Create access token
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
@limiter.limit("60/minute")
def search_courses(
    request: Request,
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

    # Identify stale courses
    stale_courses = []
    for course in courses:
        is_stale = False
        if not course.last_checked:
            is_stale = True
        else:
            time_diff = datetime.now(course.last_checked.tzinfo) - course.last_checked
            if time_diff.total_seconds() > 900:  # 15 minutes
                is_stale = True
        
        if is_stale:
            stale_courses.append(course)

    # Parallel refresh if needed
    if stale_courses:
        print(f"DEBUG: Found {len(stale_courses)} stale courses in search results. Refreshing...")
        
        def check_seat_worker(course_info):
            """Worker to check seats for a single course"""
            crn, term_code = course_info
            try:
                from workers.sniper import SeatSniper
                sniper = SeatSniper()
                result = sniper.check_seat_availability(crn, term_code)
                sniper.close()
                return (crn, result)
            except Exception as e:
                print(f"Worker failed for {crn}: {e}")
                return (crn, None)

        # Prepare work items
        work_items = [(c.crn, c.term_code) for c in stale_courses]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_crn = {executor.submit(check_seat_worker, item): item[0] for item in work_items}
            
            for future in concurrent.futures.as_completed(future_to_crn):
                crn, result = future.result()
                if result:
                    # Find and update the course object
                    course = next((c for c in courses if c.crn == crn), None)
                    if course:
                        course.seats_capacity = result['seats_capacity']
                        course.seats_available = result['seats_available']
                        course.seats_remaining = result['seats_remaining']
                        course.last_checked = result['last_checked']

        # Commit updates
        try:
            db.commit()
            # Refresh all to ensure consistency
            for course in courses:
                db.refresh(course)
        except Exception as e:
            print(f"Failed to commit batch updates: {e}")
            db.rollback()

    return courses


@app.get("/api/courses/{crn}", response_model=schemas.CourseResponse)
def get_course_by_crn(crn: str, db: Session = Depends(get_db)):
    """Get a specific course by CRN"""
    course = db.query(models.Course).filter(models.Course.crn == crn).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check for stale data (older than 15 minutes)
    is_stale = False
    if not course.last_checked:
        is_stale = True
    else:
        time_diff = datetime.now(course.last_checked.tzinfo) - course.last_checked
        if time_diff.total_seconds() > 900:  # 15 minutes
            is_stale = True

    if is_stale:
        try:
            from workers.sniper import SeatSniper
            # Run sniper check
            sniper = SeatSniper()
            seat_data = sniper.check_seat_availability(course.crn, course.term_code)
            
            if seat_data:
                # Update course in our session
                course.seats_capacity = seat_data['seats_capacity']
                course.seats_available = seat_data['seats_available']
                course.seats_remaining = seat_data['seats_remaining']
                course.last_checked = seat_data['last_checked']
                db.commit()
                db.refresh(course)
            
            sniper.close()
        except Exception as e:
            print(f"Failed to refresh stale course data: {e}")

    return course


# Track Endpoints
@app.post("/api/tracks", response_model=schemas.TrackResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_track(
    request: Request,
    track_data: schemas.TrackCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Track a course by CRN"""
    # Find the course
    course = db.query(models.Course).filter(models.Course.crn == track_data.crn).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found. Course may need to be added to inventory first.")

    # Check track limit
    track_count = db.query(models.Track).filter(
        models.Track.user_id == current_user.id,
        models.Track.is_active == True
    ).count()

    if track_count >= 10:
        raise HTTPException(status_code=400, detail="You can only track up to 10 courses.")

    # Check if already tracking
    existing_track = db.query(models.Track).filter(
        models.Track.user_id == current_user.id,
        models.Track.course_id == course.id
    ).first()

    if existing_track:
        if not existing_track.is_active:
            existing_track.is_active = True
            # Reset last_seats to current value to prevent false notifications
            existing_track.last_seats = course.seats_remaining
            existing_track.notify_on_open = track_data.notify_on_open
            existing_track.notify_on_close = track_data.notify_on_close
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

    # If course hasn't been checked recently (older than 15 mins) or is new, trigger check
    is_stale = False
    if not course.last_checked:
        is_stale = True
    else:
        # Check if older than 15 minutes
        time_diff = datetime.now(course.last_checked.tzinfo) - course.last_checked
        if time_diff.total_seconds() > 900:  # 15 minutes
            is_stale = True

    if is_stale:
        try:
            from workers.sniper import SeatSniper
            # Run sniper check
            sniper = SeatSniper()
            seat_data = sniper.check_seat_availability(course.crn, course.term_code)
            
            if seat_data:
                # Update course in our session
                course.seats_capacity = seat_data['seats_capacity']
                course.seats_available = seat_data['seats_available']
                course.seats_remaining = seat_data['seats_remaining']
                course.last_checked = seat_data['last_checked']
                
                # Also update track's last_seats to prevent false notification
                new_track.last_seats = seat_data['seats_remaining']
                
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
