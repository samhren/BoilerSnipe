# Purdue Course Sniper - Backend

FastAPI backend for tracking Purdue course seat availability.

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Install ChromeDriver** (for inventory scraper):
   - Download from: https://chromedriver.chromium.org/
   - Add to PATH or place in project directory

## Running the Application

### 1. Start the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

### 2. Run Background Workers

Start the scheduler for automated scraping and seat checking:

```bash
python -m workers.scheduler
```

This runs:
- **Inventory Scraper**: Daily at 2 AM (configurable)
- **Seat Sniper**: Every 5 minutes (configurable)

### 3. Manual Worker Execution

**Run Inventory Scraper manually:**
```bash
python -m workers.inventory_scraper
```

**Run Seat Sniper manually:**
```bash
python -m workers.sniper
```

**Test Twilio notifications:**
```bash
python -m workers.notifier +15551234567
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Courses
- `GET /api/courses` - Search courses (query params: `query`, `term_code`)
- `GET /api/courses/{crn}` - Get course details by CRN

### Tracking
- `POST /api/tracks` - Start tracking a course
- `GET /api/tracks` - Get all tracked courses
- `PATCH /api/tracks/{track_id}` - Update track settings
- `DELETE /api/tracks/{track_id}` - Stop tracking a course

## Architecture

### Phase 1: Inventory Collector
- **Tool**: Selenium WebDriver
- **Schedule**: Daily (default: 2 AM)
- **Purpose**: Scrapes Purdue's course schedule to build/update course inventory
- **Target**: https://selfservice.mypurdue.purdue.edu/prod/bwckschd.p_disp_dyn_sched
- **Process**:
  1. Select term (e.g., Spring 2026)
  2. Select subject (e.g., MA, CS, ECON)
  3. Parse course sections
  4. Extract CRN, course code, instructor, time, days
  5. Save to database

### Phase 2: Seat Sniper
- **Tool**: Python requests (lightweight, fast)
- **Schedule**: Every 5 minutes
- **Purpose**: Check seat availability for tracked courses only
- **Target**: https://selfservice.mypurdue.purdue.edu/prod/bwckschd.p_disp_detail_sched
- **Process**:
  1. Get all active user tracks
  2. For each unique CRN, fetch detail page
  3. Parse "Registration Availability" table
  4. Extract seat counts (Capacity, Actual, Remaining)
  5. Detect changes (closed → open, open → closed)
  6. Send SMS notifications via Twilio
  7. Update database

## Database Schema

### Users
- id, email, phone_number, hashed_password, is_active, created_at

### Courses
- id, crn, course_code, title, instructor, time, days, term_code, term_name
- seats_available, seats_capacity, seats_remaining
- last_checked, created_at, updated_at

### Tracks
- id, user_id, course_id
- last_status, last_seats, last_notified, last_checked
- notify_on_open, notify_on_close, is_active
- created_at

### NotificationLogs
- id, user_id, course_id
- notification_type, message, phone_number, status, error_message
- created_at

## Configuration

Edit `.env` to configure:

- **DATABASE_URL**: SQLite (default) or PostgreSQL connection string
- **SECRET_KEY**: JWT secret for authentication
- **TWILIO_***: Twilio credentials for SMS notifications
- **PROXY_URL**: Optional proxy for rotating IPs
- **INVENTORY_CRON**: Cron expression for inventory scraper schedule
- **SNIPER_INTERVAL_MINUTES**: Minutes between seat checks

## Development

**Database migrations** (if using Alembic):
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

**Reset database**:
```bash
rm purdue_courses.db
# Restart the API server to recreate tables
```
