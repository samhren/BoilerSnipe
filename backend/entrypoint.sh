#!/bin/bash

# Default to port 8000 if PORT is not set
PORT=${PORT:-8000}

# Reset database to apply schema changes (voiding past data as requested)
python reset_db.py

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
