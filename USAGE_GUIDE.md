# BoilerSnipe - Usage Guide

Operational guide for running BoilerSnipe locally.
For deployment and Google OAuth setup, see the main [README.md](README.md).

---

## Running the Application

The app has three processes: the API, the frontend, and the background scheduler.
The first two are enough to browse and track courses; the scheduler is what actually checks seats and sends alerts.

### 1. Start the Backend API

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

API docs are served at http://localhost:8000/docs

If startup fails with a Pydantic `ValidationError` for `SECRET_KEY`, that is intentional.
The key has no fallback default, so set it in `backend/.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

Visit http://localhost:5173

### 3. Start the Scheduler

```bash
cd backend
source venv/bin/activate
python -m workers.scheduler
```

This runs both background jobs:

- **Inventory Scraper**: weekly on Sunday at 2 AM (`INVENTORY_CRON`)
- **Seat Sniper**: every 5 minutes (`SNIPER_INTERVAL_MINUTES`)

---

## Running the Scrapers Manually

### Inventory Scraper

Populates the database with course sections from Purdue's schedule of classes.
It drives Selenium, so it needs Chrome and ChromeDriver, and it is slow.

```bash
cd backend
source venv/bin/activate
python -m workers.inventory_scraper

# Watch it work, for debugging
python -m workers.inventory_scraper --visible
```

Scraped subjects come from the `INVENTORY_SUBJECTS` environment variable.
Leave it unset to use the full built-in list in `app/config.py` (`DEFAULT_INVENTORY_SUBJECTS`), or narrow it while testing:

```env
INVENTORY_SUBJECTS=CS,MA,STAT
```

### Seat Sniper

Checks seat counts for actively tracked courses only, using plain HTTP requests rather than Selenium.
That is why it can run every few minutes without hammering Purdue.

```bash
cd backend
source venv/bin/activate
python -m workers.sniper
```

---

## Email Notifications

Notifications are sent by email through [Resend](https://resend.com).

1. Create an API key at https://resend.com
2. Set it in `backend/.env`:

```env
RESEND_API_KEY=re_your_key_here
```

3. Send a test email:

```bash
cd backend
source venv/bin/activate
python -m workers.notifier you@example.com
```

The sender address is configured in `workers/notifier.py`, and its domain must be verified in Resend before delivery will work.

---

## Using the App

### Create an account

Either sign in with Google, or register with an email and a password of at least 8 characters.
Google sign-in requires `VITE_GOOGLE_CLIENT_ID` (frontend) and `GOOGLE_CLIENT_ID` (backend) to be set to the same Client ID.
See the Google OAuth section of the [README](README.md) if the button does not appear or logins return 401.

### Search for courses

Search accepts several formats:

- Subject: `MA`, `CS`, `ECON`
- Course code: `MA 26100`, `CS 18000`
- CRN: `22126`
- Title: `Linear Algebra`

Results are scoped to the current term (`CURRENT_TERM_CODE`).

### Track a course

Open a course and click **Track This Course**.
You will get an email when it opens up, and optionally when it closes again.

### Manage tracked courses

The **Dashboard** lists everything you track, and lets you toggle notifications per course or stop tracking.

---

## Configuration

All settings live in `backend/.env`.
See `backend/.env.example` for the annotated full list.

### Scraper schedule

```env
INVENTORY_CRON=0 2 * * 0           # Weekly, Sunday 2 AM
SNIPER_INTERVAL_MINUTES=5          # Seat checks every 5 minutes
RUN_STARTUP_INVENTORY_ONCE=true    # One inventory scrape when the worker starts
ENABLE_RECURRING_INVENTORY=false   # Whether to also honor INVENTORY_CRON
```

Be conservative with `SNIPER_INTERVAL_MINUTES`.
It directly drives request volume against Purdue's servers.

### Term

```env
CURRENT_TERM_CODE=202710
CURRENT_TERM_NAME=Fall 2026
```

---

## Database Management

### Count courses

```bash
cd backend
source venv/bin/activate
python -c "from app.database import SessionLocal; from app.models import Course; db = SessionLocal(); print(f'Total courses: {db.query(Course).count()}')"
```

### Reset the database

```bash
cd backend
rm purdue_courses.db
# Restart the API server; tables are recreated on startup
```

This drops user accounts and tracked courses along with the course inventory.

---

## Troubleshooting

### Backend will not start, `ValidationError: SECRET_KEY Field required`

Working as designed.
Set `SECRET_KEY` in `backend/.env` rather than relying on a default.

### "No courses found"

The inventory scraper has not run yet.
Run `python -m workers.inventory_scraper` and check the count as shown above.

### Google sign-in button missing

Check the browser console for `CRITICAL: Google Client ID is missing`.
`VITE_GOOGLE_CLIENT_ID` is compiled into the bundle at build time, so restart the dev server after changing it.

### Google sign-in returns 401

The backend's `GOOGLE_CLIENT_ID` does not match the frontend's `VITE_GOOGLE_CLIENT_ID`, or is unset.
It is validated as the token audience, and a mismatch is rejected by design.

### `origin_mismatch` from Google

The origin you are browsing from is not in the OAuth client's Authorized JavaScript origins.
`localhost` and `127.0.0.1` count as different origins.
Newly added origins can take a few hours to propagate.

### Login works, then every request returns 401

`SECRET_KEY` changed between the token being issued and validated.
Rotating it invalidates all existing sessions, and the Backend and Workers services must share the same value.

### Scraper timing out

Run with `--visible` to watch the browser.
Confirm ChromeDriver matches your installed Chrome version, and that Purdue's site is reachable.

---

## Tips

- Track courses that are already full. The sniper exists to tell you the moment one frees up.
- Act fast on a notification. Popular sections refill in minutes.
- Watch the scheduler output to confirm checks are actually running on schedule.
