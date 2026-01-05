#!/bin/bash

# Default to port 8000 if PORT is not set
PORT=${PORT:-8080}

# Start the application
exec uvicorn app.main:app --host :: --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
