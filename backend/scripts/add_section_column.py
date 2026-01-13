
import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_section_column():
    """
    Adds the 'section' column to the 'courses' table if it doesn't exist.
    """
    logger.info("Checking for 'section' column in 'courses' table...")
    
    with engine.connect() as connection:
        try:
            # Check if column exists by selecting from it (simplest way in many DBs without rigorous introspection)
            # Or use pragma for sqlite
            check_query = text("SELECT section FROM courses LIMIT 1;")
            try:
                connection.execute(check_query)
                logger.info("Column 'section' already exists.")
            except Exception:
                # If selection fails, assume column missing
                logger.info("Column 'section' missing. Adding it...")
                connection.execute(text("ALTER TABLE courses ADD COLUMN section VARCHAR;"))
                connection.commit()
                logger.info("Successfully added 'section' column.")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_section_column()
