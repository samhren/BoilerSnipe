#!/bin/bash

echo "🎯 Purdue Course Sniper - Setup Script"
echo "======================================"
echo ""

# Backend setup
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env before starting the server:"
    echo "     SECRET_KEY       (required, no default - generate one below)"
    echo "     GOOGLE_CLIENT_ID (required for Google sign-in)"
    echo "     RESEND_API_KEY   (required for email notifications)"
    echo ""
    echo "   Generate a SECRET_KEY with:"
    echo "     python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
fi

cd ..

# Frontend setup
echo ""
echo "🎨 Setting up Frontend..."
cd frontend

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit backend/.env (SECRET_KEY, GOOGLE_CLIENT_ID, RESEND_API_KEY)"
echo "   and frontend/.env (VITE_GOOGLE_CLIENT_ID - same value as the backend)"
echo "2. Start backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "3. Start frontend: cd frontend && npm run dev"
echo "4. Start workers: cd backend && python -m workers.scheduler"
echo ""
echo "🚀 Happy course sniping!"
