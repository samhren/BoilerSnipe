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

# SECRET_KEY is required and has no default - the app will not start without it
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Paste that into SECRET_KEY, then fill in RESEND_API_KEY and GOOGLE_CLIENT_ID

# Start the Server
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Create .env file
cp .env.example .env
# Set VITE_GOOGLE_CLIENT_ID to the same Client ID used by the backend

# Start the Dev Server
npm run dev
```

Visit `http://localhost:5173` to see the app!

---

## Google OAuth Setup

Sign-in uses the Google Identity Services ID-token flow via `@react-oauth/google`.
The browser receives an ID token and posts it to `/api/auth/google`, which validates it server-side.
There is no server-side code exchange, so **no redirect URI and no client secret are involved**.

### 1. Create the OAuth client

In [Google Cloud Console](https://console.cloud.google.com) under **Google Auth Platform**:

**Branding**

| Field | Value |
|---|---|
| App name | `BoilerSnipe` |
| Application home page | `https://your-domain.com` |
| Privacy policy link | `https://your-domain.com/privacy` |
| Terms of service link | `https://your-domain.com/terms` |
| Authorized domains | `your-domain.com` |

Leave the app logo empty.
Uploading one puts the app into Google's brand verification queue, which takes weeks and gains you nothing.
Filling in the three App domain links requires verifying domain ownership in [Google Search Console](https://search.google.com/search-console) via a DNS TXT record.

**Audience**

Set user type to **External** and click **Publish app**.
Leaving it in Testing restricts sign-in to a manual test-user list and expires those sessions after 7 days.
This is the most common cause of "Google login suddenly stopped working".

**Data Access**

Add only `openid`, `.../auth/userinfo.email`, and `.../auth/userinfo.profile`.
All three are non-sensitive and need no review.
Any additional scope triggers a Google verification process.

**Clients → Create client**

Application type **Web application**, then add the Authorized JavaScript origins:

```
https://your-domain.com
http://localhost:5173
http://127.0.0.1:5173
```

Origins are scheme + host + port only, with no trailing slash and no path.
`localhost` and `127.0.0.1` are distinct origins to Google, so add both or local dev breaks depending on which one Vite prints.

**Leave Authorized redirect URIs empty.**

Origin changes take up to a few hours to propagate.
An `origin_mismatch` error immediately after creating the client usually just means it has not taken effect yet.

### 2. Wire up the Client ID

The same Client ID goes in two places:

```bash
# backend/.env  - the expected audience when validating ID tokens
GOOGLE_CLIENT_ID=<id>.apps.googleusercontent.com

# frontend/.env - the client that mints them
VITE_GOOGLE_CLIENT_ID=<id>.apps.googleusercontent.com
```

If these two disagree, every Google login fails with a 401.
If `GOOGLE_CLIENT_ID` is unset on the backend, `/api/auth/google` fails closed and returns 401 rather than accepting unverified tokens.

A Client ID is public by design.
The frontend one is compiled into the JS bundle, so it is not a secret and does not need rotating if credentials leak.
The client *secret* is never used by this app and should not be added to any environment.

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

### 3. Workers Service
1. Create a second service from the same GitHub repository.
2. **Settings** -> **Root Directory**: `backend`
3. **Variables**: the same set as the Backend service.
   `SECRET_KEY` in particular must be **identical** to the Backend's.
4. Additionally set:
   - `RUN_STARTUP_INVENTORY_ONCE`: `true`
   - `ENABLE_RECURRING_INVENTORY`: `true`

This service runs `workers/scheduler.py` (the inventory scraper and seat sniper) rather than the API.
Keeping it separate means a long Selenium scrape cannot block API requests.

### 4. Frontend Service
1. Create a new service from your GitHub repository.
2. **Settings** -> **Root Directory**: `frontend`
3. **Variables**:
   - `BACKEND_URL`: The **private** address of your Backend service (e.g., `http://backend.railway.internal:8080`). Caddy proxies `/api/*` there, so the browser talks to a single origin.
   - `VITE_GOOGLE_CLIENT_ID`: Your Google OAuth Client ID.
   - `PORT`: `80` (Caddy listens on 80 inside the container, Railway maps it).
4. **Networking**: Generate a Public Domain for this service to access the UI.

Leave `VITE_API_URL` unset in production.
The Caddy reverse proxy serves the API from the same origin, which avoids CORS entirely.

> **`VITE_GOOGLE_CLIENT_ID` is a build argument, not a runtime variable** (see `frontend/Dockerfile`).
> Vite compiles it into the JS bundle at build time, so changing it requires a **rebuild**.
> A plain restart or a redeploy that reuses the cached build will keep serving the old Client ID.

Set `FRONTEND_URL` on the Backend to your public domain.
It is what gets appended to the CORS allowlist in `app/main.py`, and omitting it makes every browser request fail CORS.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | DB Connection string (e.g., `sqlite:///./purdue.db`) | Yes |
| `SECRET_KEY` | Secret for signing JWTs. **No default** - the app refuses to start without it. Must match across Backend and Workers. Rotating it logs out every user. | Yes |
| `RESEND_API_KEY` | API Key for sending emails | Yes |
| `GOOGLE_CLIENT_ID` | OAuth Client ID, used as the expected audience when validating Google ID tokens. Must match `VITE_GOOGLE_CLIENT_ID`. If unset, `/api/auth/google` fails closed with a 401. | Yes |
| `FRONTEND_URL` | Public frontend origin, appended to the CORS allowlist | Yes (Prod) |
| `ALLOWED_HOSTS` | Trusted Host allowlist, use `*` when behind a reverse proxy | No |
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
| `VITE_API_URL` | Backend API URL. Local dev only - leave **unset** in production, where Caddy proxies `/api/*` same-origin. | Local only |
| `VITE_GOOGLE_CLIENT_ID` | OAuth Client ID for React. Baked in at **build time**, so changing it requires a rebuild. | Yes |
| `BACKEND_URL` | Internal address Caddy proxies `/api/*` to (production) | Yes (Prod) |

---

## Security Notes

- **`SECRET_KEY` has no fallback default.** A missing value raises a Pydantic `ValidationError` at startup instead of silently signing JWTs with a value that is public in this repo.
- **Google ID tokens are validated against `GOOGLE_CLIENT_ID` as the audience.** Skipping that check would mean only verifying that *Google* issued the token, not that it was issued to *this app*, which lets any Google ID token from any unrelated site authenticate as its owner.
- **Never commit a `.env` file.** Both `.env` files are gitignored; only `.env.example` belongs in version control.
- **Client IDs are public, client secrets are not used.** This app never performs a server-side code exchange, so there is no reason for an OAuth client secret to exist in any environment.
- Enable **Secret scanning** and **Push protection** in GitHub repo settings.
  Both are free on public repos and block a leaked credential at push time rather than after it is in history.

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
