
import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from sqlalchemy import inspect, text

def migrate_section_column():
    """
    Adds the 'section' column to the 'courses' table if it doesn't exist.
    """
    logger.info("Checking for 'section' column in 'courses' table...")
    
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('courses')]
    
    if 'section' in columns:
        logger.info("Column 'section' already exists.")
    else:
        logger.info("Column 'section' missing. Adding it...")
        with engine.begin() as connection:
             connection.execute(text("ALTER TABLE courses ADD COLUMN section VARCHAR;"))
        logger.info("Successfully added 'section' column.")

if __name__ == "__main__":
    migrate_section_column()
