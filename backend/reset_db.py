import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.database import engine, Base
from app import models  # Important: Import models so they are registered in metadata

def reset_database():
    print("⚠️  RESETTING DATABASE...")
    try:
        # Drop all tables
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Create all tables (with new schema)
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database reset complete.")
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()
