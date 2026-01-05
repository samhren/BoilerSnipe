# 🎯 Purdue Course Sniper

A full-stack web application that monitors Purdue course seat availability and sends instant SMS notifications when seats become available.

## Features

- 🔍 **Smart Course Search** - Search by subject, course code, or CRN
- 🎯 **Real-time Monitoring** - Checks seat availability every 5 minutes
- 📱 **SMS Notifications** - Instant text alerts via Twilio
- 🔐 **User Authentication** - Secure JWT-based auth
- 📊 **Dashboard** - Track multiple courses with live status updates
- ⚡ **Efficient Architecture** - Two-phase system minimizes server load

## Architecture

### Phase 1: Inventory Collector (Daily)
- **Tool**: Selenium WebDriver
- **Frequency**: Daily at 2 AM (configurable)
- **Purpose**: Builds/updates course inventory from Purdue's schedule
- **Process**:
  1. Navigate to Purdue's schedule search
  2. Select term and subjects
  3. Extract CRN, course code, instructor, time, days
  4. Store in database

### Phase 2: Seat Sniper (Every 5 Minutes)
- **Tool**: Python `requests` library
- **Frequency**: Every 5 minutes (configurable)
- **Purpose**: Checks seat availability for tracked courses only
- **Process**:
  1. Query database for actively tracked courses
  2. Fetch seat details for each unique CRN
  3. Parse registration availability
  4. Detect seat status changes
  5. Send SMS notifications via Twilio
  6. Update database

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database management
- **Selenium** - Web scraping for inventory collection
- **Requests** - HTTP library for seat checking
- **Twilio** - SMS notifications
- **APScheduler** - Background job scheduling
- **PostgreSQL/SQLite** - Database

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Chrome/Chromium browser (for Selenium)
- ChromeDriver (matching your Chrome version)
- Twilio account (for SMS notifications)

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (Twilio credentials, etc.)

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

### 3. Start Background Workers

```bash
# In backend directory
python -m workers.scheduler
```

## Configuration

### Backend (.env)

```env
# Database
DATABASE_URL=sqlite:///./purdue_courses.db

# JWT
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+15551234567

# Scraper Settings
INVENTORY_CRON=0 2 * * *          # Daily at 2 AM
SNIPER_INTERVAL_MINUTES=5          # Check every 5 minutes
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

## Usage

1. **Sign Up**: Create an account with your email and phone number
2. **Search Courses**: Find courses by subject (MA), course code (MA 35100), or CRN
3. **Track Courses**: Click "Track This Course" on courses you want to monitor
4. **Get Notified**: Receive SMS when a seat opens up
5. **Register Fast**: Use the notification to quickly register before seats fill!

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Courses
- `GET /api/courses?query={search}` - Search courses
- `GET /api/courses/{crn}` - Get course by CRN

### Tracking
- `POST /api/tracks` - Start tracking a course
- `GET /api/tracks` - Get all tracked courses
- `PATCH /api/tracks/{id}` - Update track settings
- `DELETE /api/tracks/{id}` - Stop tracking

## Manual Worker Execution

### Run Inventory Scraper
```bash
cd backend
python -m workers.inventory_scraper
```

### Run Seat Sniper
```bash
cd backend
python -m workers.sniper
```

### Test Notifications
```bash
cd backend
python -m workers.notifier +15551234567
```

## Database Schema

### Users
- Email, phone number, hashed password
- Created timestamp

### Courses
- CRN (unique identifier)
- Course code, title, instructor
- Time, days, term
- Seat availability (capacity, remaining)
- Last checked timestamp

### Tracks
- User-course relationship
- Notification preferences
- Last status, last notified
- Active/inactive flag

### NotificationLogs
- Notification history
- User, course, message
- Status (sent/failed)
- Timestamp

## Project Structure

```
PurdueCourseNotify/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # Database models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── auth.py              # JWT authentication
│   │   ├── database.py          # DB connection
│   │   └── config.py            # Settings
│   ├── workers/
│   │   ├── inventory_scraper.py # Phase 1: Selenium scraper
│   │   ├── sniper.py            # Phase 2: Seat checker
│   │   ├── notifier.py          # Twilio SMS service
│   │   └── scheduler.py         # APScheduler jobs
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API client
│   │   ├── hooks/               # Custom hooks (useAuth)
│   │   ├── App.jsx              # Main app
│   │   └── main.jsx             # Entry point
│   └── package.json
└── README.md
```

## Development

### Adding New Subjects to Scraper

Edit `backend/workers/scheduler.py`:

```python
subjects=["MA", "CS", "ECON", "STAT", "PHYS", "CHEM", "BIOL"]
```

### Changing Check Frequency

Edit `backend/.env`:

```env
SNIPER_INTERVAL_MINUTES=3  # Check every 3 minutes instead of 5
```

### Using PostgreSQL Instead of SQLite

Edit `backend/.env`:

```env
DATABASE_URL=postgresql://user:password@localhost/purdue_courses
```

## Deployment

### Backend (FastAPI)
- Deploy to Heroku, Railway, or DigitalOcean
- Set environment variables
- Run migrations if using PostgreSQL
- Start background workers as separate processes

### Frontend (React)
- Build: `npm run build`
- Deploy to Vercel, Netlify, or static hosting
- Update VITE_API_URL to production API URL

## Important Notes

⚠️ **Rate Limiting**: Be respectful of Purdue's servers. Default 5-minute intervals are reasonable.

⚠️ **ChromeDriver**: Ensure ChromeDriver version matches your Chrome browser version.

⚠️ **Twilio Costs**: SMS notifications incur costs. Monitor usage in your Twilio dashboard.

⚠️ **Academic Use**: This tool is for educational purposes. Always follow Purdue's terms of service.

## Troubleshooting

### "ChromeDriver not found"
- Download ChromeDriver: https://chromedriver.chromium.org/
- Add to PATH or place in project directory

### "Twilio authentication failed"
- Verify credentials in `.env`
- Check Twilio dashboard for account status

### "Database locked" errors with SQLite
- Use PostgreSQL for production
- Ensure only one scheduler is running

### Frontend can't connect to backend
- Verify backend is running on port 8000
- Check CORS settings in `backend/app/main.py`
- Verify VITE_API_URL in frontend `.env`

## Contributing

This is an educational project. Feel free to fork and customize for your needs!

## License

MIT License - See LICENSE file for details

## Disclaimer

This project is not affiliated with or endorsed by Purdue University. Use responsibly and in accordance with university policies.

---

Built with ❤️ for Boilermakers who want to get into their classes!
