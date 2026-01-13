
import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_grade_distributions():
    """
    Drops the 'grade_distributions' table.
    """
    logger.info("Dropping 'grade_distributions' table...")
    
    with engine.begin() as connection:
        try:
            connection.execute(text("DROP TABLE IF EXISTS grade_distributions;"))
            logger.info("Successfully dropped 'grade_distributions' table.")
        except Exception as e:
            logger.error(f"Failed to drop table: {e}")

if __name__ == "__main__":
    drop_grade_distributions()
