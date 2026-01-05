import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """
    Checks for missing columns and adds them if necessary.
    """
    logger.info("Starting database migration check...")
    
    with engine.connect() as connection:
        # Check if google_id column exists in users table
        # We use a safe parameterized query to check information_schema or just try/except.
        # Postgres specific check:
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='google_id';
        """)
        
        result = connection.execute(check_query).fetchone()
        
        if not result:
            logger.info("Adding missing column 'google_id' to 'users' table...")
            try:
                # Add the column
                connection.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR UNIQUE;"))
                # Create index (implicitly created by UNIQUE constraint usually, but strictly speaking explicitly asking for index in model)
                # Let's just stick to the column for now to fix the crash.
                connection.commit()
                logger.info("Successfully added 'google_id' column.")
            except Exception as e:
                logger.error(f"Failed to add column: {e}")
                raise e
        else:
            logger.info("Column 'google_id' already exists.")

if __name__ == "__main__":
    migrate()
