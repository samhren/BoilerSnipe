# 🎯 Purdue Course Sniper - Usage Guide

## ✅ Current Status

Your application is **fully functional** with:
- ✅ **507 courses** in the database (MA courses scraped)
- ✅ Backend API running on http://localhost:8000
- ✅ Frontend React app running on http://localhost:5173
- ✅ Authentication working (JWT)
- ✅ Inventory scraper working
- ✅ Seat sniper ready
- ✅ Twilio SMS integration ready (needs credentials)

---

## 🚀 Running the Application

### 1. Start Backend API

```bash
cd /Users/samhren/Code/PurdueCourseNotify/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 2. Start Frontend

```bash
cd /Users/samhren/Code/PurdueCourseNotify/frontend
npm run dev
```

### 3. Open App

Visit: **http://localhost:5173**

---

## 📊 Running the Scrapers

### Inventory Scraper (Phase 1)

Populates the database with courses from Purdue.

**Run in headless mode (production):**
```bash
cd /Users/samhren/Code/PurdueCourseNotify/backend
source venv/bin/activate
python -m workers.inventory_scraper
```

**Run in visible mode (debugging):**
```bash
python -m workers.inventory_scraper --visible
# or
python -m workers.inventory_scraper -v
```

**What it scrapes:**
- Subjects: MA, CS, ECON, STAT, PHYS, CHEM, BIOL, ENGR, MGMT, ECE, ME, IE, AAE, ABE, CHE, CE, MSE, NE
- Term: Fall 2026 (202710)
- You can edit the subjects list in `workers/inventory_scraper.py` lines 335-346

### Seat Sniper (Phase 2)

Checks seat availability for tracked courses and sends SMS notifications.

**Run once (manual test):**
```bash
cd /Users/samhren/Code/PurdueCourseNotify/backend
source venv/bin/activate
python -m workers.sniper
```

**Run scheduler (automatic - recommended):**
```bash
cd /Users/samhren/Code/PurdueCourseNotify/backend
source venv/bin/activate
python -m workers.scheduler
```

This runs:
- **Inventory Scraper**: Weekly on Sunday at 2 AM
- **Seat Sniper**: Every 5 minutes

---

## 📱 SMS Notifications Setup

1. Sign up at https://www.twilio.com/
2. Get your credentials from the Twilio Console
3. Edit `backend/.env`:

```env
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567
```

4. Test notifications:
```bash
cd backend
source venv/bin/activate
python -m workers.notifier +15551234567
```

---

## 🎓 How to Use the App

### 1. Create Account
1. Go to http://localhost:5173
2. Click "Sign Up"
3. Enter:
   - Email
   - Phone number (10 digits for SMS)
   - Password (min 8 characters)

### 2. Search for Courses
1. Click "Search Courses"
2. Search by:
   - Subject: `MA`, `CS`, `ECON`, etc.
   - Course code: `MA 26100`, `CS 18000`
   - CRN: `22126`
   - Title: `Linear Algebra`

### 3. Track a Course
1. Find the course you want
2. Click "Track This Course"
3. You'll receive SMS when:
   - Seats open up (if you enabled notifications)
   - Course fills up (optional)

### 4. Manage Your Tracks
1. Go to "Dashboard"
2. See all tracked courses
3. Toggle notifications on/off
4. Stop tracking courses

---

## 🔧 Configuration

### Change Scraper Schedule

Edit `backend/.env`:

```env
# Weekly on Sunday at 2 AM
INVENTORY_CRON=0 2 * * 0

# Check every 3 minutes instead of 5
SNIPER_INTERVAL_MINUTES=3
```

### Change Term to Scrape

Edit `backend/.env`:

```env
CURRENT_TERM_CODE=202710
CURRENT_TERM_NAME=Fall 2026
```

### Add/Remove Subjects

Edit `backend/workers/inventory_scraper.py` lines 335-346:

```python
subjects_to_scrape = [
    "MA",      # Mathematics
    "CS",      # Computer Science
    "ECON",    # Economics
    # Add more subjects here...
]
```

---

## 📈 Database Management

### Check Course Count
```bash
cd backend
source venv/bin/activate
python -c "from app.database import SessionLocal; from app.models import Course; db = SessionLocal(); print(f'Total courses: {db.query(Course).count()}')"
```

### Clear All Courses
```bash
python -c "from app.database import SessionLocal; from app.models import Course; db = SessionLocal(); db.query(Course).delete(); db.commit(); print('All courses deleted')"
```

### Reset Entire Database
```bash
cd backend
rm purdue_courses.db
# Restart the backend - tables will be recreated
```

---

## 🐛 Troubleshooting

### "No courses found"
- Run the inventory scraper first: `python -m workers.inventory_scraper`
- Check if courses are in DB: See "Check Course Count" above

### "Login not working"
- Make sure backend is running on port 8000
- Check browser console for errors
- Try clearing localStorage and logging in again

### "SMS not sending"
- Check Twilio credentials in `.env`
- Test with: `python -m workers.notifier +15551234567`
- Verify phone number format: `+15551234567` (include +1)

### "Scraper timing out"
- Run in visible mode to debug: `python -m workers.inventory_scraper --visible`
- Check internet connection
- Verify Purdue website is accessible

---

## 📊 Current Database Statistics

- **Total Courses**: 507
- **Subjects**: MA (Mathematics)
- **Term**: Fall 2026 (202710)

**Sample Courses Available:**
- MA 13700: Mathematics For Elementary Teachers I
- MA 13800: Mathematics For Elementary Teachers II
- MA 16010: Applied Calculus I
- MA 16100: Plane Analytic Geometry And Calculus I
- MA 16500: Analytic Geometry And Calculus I
- MA 16600: Analytic Geometry And Calculus II
- MA 26100: Multivariate Calculus
- MA 26500: Linear Algebra
- MA 26600: Ordinary Differential Equations
- MA 35100: Elementary Linear Algebra
- And 497 more...

---

## 🎯 Next Steps

1. ✅ **Try the app**: Create an account and track a course
2. ⚙️ **Configure Twilio**: Set up SMS notifications
3. 🤖 **Run scheduler**: Start automated seat checking
4. 📚 **Scrape more**: Add more subjects to the scraper
5. 🚀 **Deploy**: Consider deploying to a server for 24/7 monitoring

---

## 💡 Tips

- **Track closed courses**: The sniper will notify you when seats open
- **Multiple courses**: Track as many as you want
- **Be fast**: When you get a notification, register quickly!
- **Test first**: Use sample courses to test before tracking real ones
- **Check logs**: Monitor the scheduler output to see when checks run

---

**Need help?** Check the main README.md or the backend/README.md for more detailed information.
