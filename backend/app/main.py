from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, and_
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
from .migrate import migrate

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
    init_db()
    migrate()


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
    term_code: str = settings.CURRENT_TERM_CODE,
    db: Session = Depends(get_db)
):
    """Search courses in the database"""
    courses_query = db.query(models.Course).filter(models.Course.is_listed == True)

    if term_code:
        courses_query = courses_query.filter(models.Course.term_code == term_code)

    if query:
        import re
        # Normalize: remove extra spaces
        clean_query = " ".join(query.strip().split())
        subject_match = re.fullmatch(r'[a-zA-Z]{2,6}', clean_query)
        
        if subject_match:
            # Exact subject-prefix searches like "CS" should not return courses
            # whose title merely contains those letters.
            courses_query = courses_query.filter(models.Course.course_code.ilike(f"{clean_query} %"))
        else:
            conditions = []
            
            # 1. CRN Match
            conditions.append(models.Course.crn.ilike(f"%{clean_query}%"))
            
            # 2. Smart Course Code Match (handles "CS180", "cs 180" -> matches "CS 18000")
            code_match = re.match(r'^([a-zA-Z]+)[\s-]*(\d+)$', clean_query)
            if code_match:
                subj, num = code_match.groups()
                conditions.append(models.Course.course_code.ilike(f"{subj}%{num}%"))
                
            # 3. Token-based matching (AND logic for terms)
            terms = clean_query.split()
            if terms:
                # Title: All terms must match
                conditions.append(and_(*[models.Course.title.ilike(f"%{term}%") for term in terms]))
                # Course Code: All terms must match (e.g. "CS 180")
                conditions.append(and_(*[models.Course.course_code.ilike(f"%{term}%") for term in terms]))
                
            courses_query = courses_query.filter(or_(*conditions))
            
    courses = courses_query.order_by(models.Course.course_code, models.Course.section, models.Course.crn).limit(50).all()

    # Process courses to hide seat data for untracked courses
    for course in courses:
        # Check if course has any active tracks
        has_active_tracks = any(t.is_active for t in course.tracks)
        
        if not has_active_tracks:
            # Set placeholder values for untracked courses
            course.seats_capacity = 999
            course.seats_available = 999
            course.seats_remaining = 999

    return courses


@app.get("/api/courses/{crn}", response_model=schemas.CourseResponse)
def get_course_by_crn(
    crn: str,
    term_code: str = settings.CURRENT_TERM_CODE,
    db: Session = Depends(get_db)
):
    """Get a specific course by CRN"""
    course = db.query(models.Course).filter(
        models.Course.crn == crn,
        models.Course.term_code == term_code,
        models.Course.is_listed == True
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if course has any active tracks
    has_active_tracks = any(t.is_active for t in course.tracks)

    if not has_active_tracks:
        # Set placeholder values for untracked courses
        course.seats_capacity = 999
        course.seats_available = 999
        course.seats_remaining = 999

    return course


# Grade Distribution Endpoints
@app.get("/api/grades/{course_code}", response_model=schemas.GradeDistributionSummary)
@limiter.limit("60/minute")
def get_grade_distribution(
    request: Request,
    course_code: str,
    instructor: str = None,
    db: Session = Depends(get_db)
):
    """
    Get grade distribution for a course.

    course_code: Course code like "CS 18000" or "MA 26100"
    instructor: Optional filter by instructor name (partial match)
    """
    # Parse course_code into subject and number
    parts = course_code.strip().split()
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid course code format. Use 'CS 18000' format.")

    subject = parts[0].upper()
    course_number = parts[1]

    # Load from JSON store instead of DB
    from . import grades_store
    records = grades_store.get_by_course(subject, course_number, instructor)

    if not records:
        raise HTTPException(status_code=404, detail="No grade data found for this course")

    # Calculate aggregates
    def safe_avg(values):
        valid = [v for v in values if v is not None]
        return sum(valid) / len(valid) if valid else None

    def combine_grades(*fields):
        """Sum multiple grade fields for a record"""
        values = []
        for record in records:
            total = 0
            count = 0
            for field in fields:
                val = getattr(record, field, None)
                if val is not None:
                    total += val
                    count += 1
            if count > 0:
                values.append(total)
        return values

    # Build response
    return schemas.GradeDistributionSummary(
        subject=subject,
        course_number=course_number,
        title=records[0].title,
        total_sections=len(records),
        semesters=list(set(r.academic_period_desc for r in records if r.academic_period_desc)),
        instructors=list(set(r.instructor for r in records if r.instructor)),
        # Combined averages
        avg_a=safe_avg(combine_grades('grade_a_plus', 'grade_a', 'grade_a_minus')),
        avg_b=safe_avg(combine_grades('grade_b_plus', 'grade_b', 'grade_b_minus')),
        avg_c=safe_avg(combine_grades('grade_c_plus', 'grade_c', 'grade_c_minus')),
        avg_d=safe_avg(combine_grades('grade_d_plus', 'grade_d', 'grade_d_minus')),
        avg_f=safe_avg(combine_grades('grade_e', 'grade_f')),
        avg_w=safe_avg([r.grade_w for r in records]),
        # Individual plus/minus breakdowns
        avg_a_plus=safe_avg([r.grade_a_plus for r in records]),
        avg_a_base=safe_avg([r.grade_a for r in records]),
        avg_a_minus=safe_avg([r.grade_a_minus for r in records]),
        avg_b_plus=safe_avg([r.grade_b_plus for r in records]),
        avg_b_base=safe_avg([r.grade_b for r in records]),
        avg_b_minus=safe_avg([r.grade_b_minus for r in records]),
        avg_c_plus=safe_avg([r.grade_c_plus for r in records]),
        avg_c_base=safe_avg([r.grade_c for r in records]),
        avg_c_minus=safe_avg([r.grade_c_minus for r in records]),
        avg_d_plus=safe_avg([r.grade_d_plus for r in records]),
        avg_d_base=safe_avg([r.grade_d for r in records]),
        avg_d_minus=safe_avg([r.grade_d_minus for r in records]),
        records=[schemas.GradeDistributionResponse.model_validate(r.__dict__) for r in records]
    )


@app.get("/api/grades", response_model=List[schemas.GradeDistributionResponse])
@limiter.limit("60/minute")
def search_grades(
    request: Request,
    subject: str = None,
    course_number: str = None,
    instructor: str = None,
    academic_period: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search grade distributions with flexible filters (JSON-backed)."""
    from . import grades_store
    results = grades_store.search(subject, course_number, instructor, academic_period, limit)
    # Convert to Pydantic-compatible dicts
    return [schemas.GradeDistributionResponse.model_validate(r.__dict__) for r in results]


# Track Endpoints
@app.post("/api/tracks", response_model=schemas.TrackResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_track(
    request: Request,
    track_data: schemas.TrackCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Track a course by term-scoped CRN"""
    # Find the course
    course = db.query(models.Course).filter(
        models.Course.crn == track_data.crn,
        models.Course.term_code == track_data.term_code,
        models.Course.is_listed == True
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found. Course may need to be added to inventory first.")

    # Check track limit
    track_count = db.query(models.Track).join(models.Course).filter(
        models.Track.user_id == current_user.id,
        models.Track.is_active == True,
        models.Course.term_code == settings.CURRENT_TERM_CODE,
        models.Course.is_listed == True
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
    """Get active tracks for current-term listed courses."""
    tracks = db.query(models.Track).join(models.Course).filter(
        models.Track.user_id == current_user.id,
        models.Track.is_active == True,
        models.Course.term_code == settings.CURRENT_TERM_CODE,
        models.Course.is_listed == True
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
