#!/bin/bash

# Default to port 8000 if PORT is not set
PORT=${PORT:-8080}

# Run database migrations
python -m app.migrate

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
