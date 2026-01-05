# Purdue Course Sniper - Frontend

React + Vite + Tailwind CSS frontend for tracking Purdue course seat availability.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env if needed (default points to http://localhost:8000)
   ```

## Development

Start the development server:

```bash
npm run dev
```

Frontend will be available at: http://localhost:5173

## Build for Production

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Features

### Authentication
- User registration with email and phone number
- JWT-based login/logout
- Protected routes for authenticated users

### Course Search
- Search by subject code (e.g., "MA", "CS")
- Search by course code (e.g., "MA 35100")
- Search by CRN (e.g., "22126")
- Search by course title (e.g., "Linear Algebra")

### Dashboard
- View all tracked courses
- Real-time seat availability status
- Statistics: Total tracked, Open seats, Closed seats
- Configure notification preferences per course
- Stop tracking courses

### Notifications
- Toggle SMS notifications when seats open
- Toggle SMS notifications when seats close
- View last notification time

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Navbar.jsx           # Navigation bar
│   │   ├── CourseCard.jsx       # Course display card
│   │   ├── TrackCard.jsx        # Tracked course card
│   │   └── ProtectedRoute.jsx   # Auth route guard
│   ├── pages/
│   │   ├── Home.jsx             # Landing page
│   │   ├── Login.jsx            # Login page
│   │   ├── Register.jsx         # Registration page
│   │   ├── Dashboard.jsx        # User dashboard
│   │   └── Search.jsx           # Course search page
│   ├── services/
│   │   └── api.js               # API client (axios)
│   ├── hooks/
│   │   └── useAuth.js           # Authentication context
│   ├── App.jsx                  # Main app component
│   ├── main.jsx                 # Entry point
│   └── index.css                # Tailwind styles
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## Color Scheme

The app uses Purdue's official colors:
- **Purdue Gold**: `#CFB991`
- **Purdue Black**: `#000000`

## API Integration

The frontend communicates with the FastAPI backend through:
- `/api/auth/*` - Authentication endpoints
- `/api/courses` - Course search
- `/api/tracks` - Track management

API requests automatically include JWT tokens for authenticated endpoints.
