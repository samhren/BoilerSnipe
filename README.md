# BoilerSnipe

> **Purdue Course Availability Tracker & Sniper**

**Live at [boilersnipe.com](https://boilersnipe.com/)**

BoilerSnipe is a full-stack web application that monitors Purdue University course seat availability in real-time. Students can track specific courses and receive instant **Email Notifications** when a seat becomes available.

## Features

- **Smart Course Search**: Instantly find courses by Subject, Course Code, or CRN.
- **Real-time Monitoring**: Automatically checks seat availability every few minutes.
- **Instant Alerts**: Receive emails immediately when a spot opens up (via Resend).
- **Modern Auth**: Secure login with **Google Single Sign-On (SSO)**.
- **Live Dashboard**: View status of all your tracked courses in one place.
- **Dockerized**: Fully containerized for consistent deployment.

---

## Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10)
- **Database**: PostgreSQL (Production) / SQLite (Dev)
- **Scraping**: Selenium & Chromium (for daily inventory), `requests` (for fast seat checking)
- **Scheduling**: APScheduler (Background workers)
- **Notifications**: [Resend](https://resend.com/) (Email)
- **Auth**: Google OAuth & JWT

### Frontend
- **Framework**: React 18 (Vite)
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **Server**: Caddy (Production static serving & proxy)

---

## Quick Start (Local Development)

### Prerequisites
- Node.js 18+
- Python 3.10+
- Chrome & ChromeDriver (for local scraping)
- PostgreSQL (optional, defaults to SQLite locally)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Update .env with your credentials (RESEND_API_KEY, GOOGLE_CLIENT_ID, etc.)

# Start the Server
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Create .env file
cp .env.example .env

# Start the Dev Server
npm run dev
```

Visit `http://localhost:5173` to see the app!

---

## Deployment on Railway

This project is optimized for deployment on [Railway](https://railway.app/).

### 1. Database (PostgreSQL)
1. Create a new service in your Railway project.
2. Select **Database** -> **PostgreSQL**.
3. Railway will provide a `DATABASE_URL` variable automatically.

### 2. Backend Service
1. Create a new service from your GitHub repository.
2. **Settings** -> **Root Directory**: `backend`
3. **Variables**:
   - `DATABASE_URL`: `${{PostgreSQL.DATABASE_URL}}` (Reference your DB service)
   - `SECRET_KEY`: Generate a strong random string.
   - `RESEND_API_KEY`: Your API key from Resend.com.
   - `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID.
   - `SNIPER_INTERVAL_MINUTES`: `5` (Recommended)
   - `PORT`: `8080` (Railway expects this)
4. Railway will automatically detect the `Dockerfile` in `/backend` and build it.

### 3. Frontend Service
1. Create a new service from your GitHub repository.
2. **Settings** -> **Root Directory**: `frontend`
3. **Variables**:
   - `VITE_API_URL`: The **Public Domain** of your Backend Service (e.g., `https://backend-production.up.railway.app`).
   - `VITE_GOOGLE_CLIENT_ID`: Your Google OAuth Client ID.
   - `PORT`: `80` (Caddy listens on 80 inside the container, Railway maps it).
4. **Networking**: Generate a Public Domain for this service to access the UI.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | DB Connection string (e.g., `sqlite:///./purdue.db`) | Yes |
| `SECRET_KEY` | Secret for JWT encryption | Yes |
| `RESEND_API_KEY` | API Key for sending emails | Yes |
| `GOOGLE_CLIENT_ID` | OAuth Client ID for backend validation | Yes |
| `SNIPER_INTERVAL_MINUTES` | Frequency of seat checks (default: 5) | No |
| `INVENTORY_CRON` | Cron schedule for full course scrape (default: `0 2 * * 0`, weekly Sunday at 2 AM) | No |
| `CURRENT_TERM_CODE` | Default Purdue term code to scrape and search | No |
| `CURRENT_TERM_NAME` | Display name for the default term | No |
| `INVENTORY_SUBJECTS` | Comma-separated subject list for inventory scraping | No |
| `RUN_STARTUP_INVENTORY_ONCE` | Run current-term inventory once on each worker start (default: `true`) | No |
| `ENABLE_RECURRING_INVENTORY` | Keep inventory on cron after startup scrape (default: `false`) | No |

### Frontend (`frontend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_API_URL` | URL of the backend API | Yes (Prod only) |
| `VITE_GOOGLE_CLIENT_ID` | OAuth Client ID for React | Yes |

---

## 🏗️ Architecture

The system operates in two phases to minimize load on Purdue's servers:

1.  **Inventory Collection (Daily)**: 
    - Runs once a day (default 2 AM).
    - Uses **Selenium** to browse Purdue's course catalog.
    - Updates local database with *all* available courses/CRNs.

2.  **Seat Sniper (Interval)**:
    - Runs frequently (e.g., every 5 mins).
    - Uses lightweight HTTP **Requests** to check seat counts *only* for courses that users are actively tracking.
    - Triggers notifications immediately upon status change.

---

## License

MIT License.
**Disclaimer**: This project is not affiliated with Purdue University. Use responsibly.
