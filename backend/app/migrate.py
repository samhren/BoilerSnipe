import logging
import sqlite3
from pathlib import Path

from sqlalchemy import inspect, text

from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_google_id(inspector) -> None:
    if "users" not in inspector.get_table_names():
        return

    if "google_id" in _column_names(inspector, "users"):
        return

    logger.info("Adding missing column 'google_id' to 'users' table...")
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR"))


def _ensure_app_state_table() -> None:
    if engine.dialect.name == "sqlite":
        statement = """
            CREATE TABLE IF NOT EXISTS app_state (
                key VARCHAR NOT NULL PRIMARY KEY,
                value VARCHAR,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        statement = """
            CREATE TABLE IF NOT EXISTS app_state (
                key VARCHAR NOT NULL PRIMARY KEY,
                value VARCHAR,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """

    with engine.begin() as connection:
        connection.execute(text(statement))


def _sqlite_courses_need_rebuild(inspector) -> bool:
    if "courses" not in inspector.get_table_names():
        return False

    columns = _column_names(inspector, "courses")
    required_columns = {"schedule_type", "section", "is_listed"}
    if not required_columns.issubset(columns):
        return True

    unique_constraints = inspector.get_unique_constraints("courses")
    if any(constraint.get("column_names") == ["crn"] for constraint in unique_constraints):
        return True

    indexes = inspector.get_indexes("courses")
    if any(index.get("unique") and index.get("column_names") == ["crn"] for index in indexes):
        return True

    return False


def _rebuild_sqlite_courses_table() -> None:
    logger.info("Rebuilding SQLite 'courses' table for term-scoped CRNs...")
    inspector = inspect(engine)
    old_columns = _column_names(inspector, "courses")

    def existing_or_default(column_name: str, default_sql: str) -> str:
        return column_name if column_name in old_columns else default_sql

    insert_sql = f"""
        INSERT INTO courses_new (
            id, crn, course_code, title, instructor, time, days, schedule_type,
            term_code, term_name, section, is_listed, seats_available, seats_capacity,
            seats_remaining, last_checked, created_at, updated_at
        )
        SELECT
            id,
            crn,
            course_code,
            title,
            instructor,
            time,
            days,
            {existing_or_default("schedule_type", "NULL")},
            term_code,
            term_name,
            {existing_or_default("section", "NULL")},
            {existing_or_default("is_listed", "1")},
            seats_available,
            seats_capacity,
            seats_remaining,
            last_checked,
            created_at,
            updated_at
        FROM courses
    """

    database_path = Path(engine.url.database or "").resolve()
    script = f"""
    PRAGMA foreign_keys=OFF;
    DROP TABLE IF EXISTS courses_new;
    CREATE TABLE courses_new (
        id INTEGER NOT NULL PRIMARY KEY,
        crn VARCHAR NOT NULL,
        course_code VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        instructor VARCHAR,
        time VARCHAR,
        days VARCHAR,
        schedule_type VARCHAR,
        term_code VARCHAR NOT NULL,
        term_name VARCHAR,
        section VARCHAR,
        is_listed BOOLEAN NOT NULL DEFAULT 1,
        seats_available INTEGER,
        seats_capacity INTEGER,
        seats_remaining INTEGER,
        last_checked DATETIME,
        created_at DATETIME,
        updated_at DATETIME
    );
    {insert_sql};
    DROP TABLE courses;
    ALTER TABLE courses_new RENAME TO courses;
    CREATE INDEX ix_courses_id ON courses (id);
    CREATE INDEX ix_courses_crn ON courses (crn);
    CREATE INDEX ix_courses_course_code ON courses (course_code);
    CREATE INDEX ix_courses_term_code ON courses (term_code);
    CREATE UNIQUE INDEX uq_courses_term_crn ON courses (term_code, crn);
    CREATE INDEX ix_courses_term_listed_code ON courses (term_code, is_listed, course_code);
    PRAGMA foreign_keys=ON;
    """

    with sqlite3.connect(database_path) as connection:
        connection.executescript(script)
        connection.commit()


def _migrate_sqlite() -> None:
    inspector = inspect(engine)
    _ensure_google_id(inspector)

    inspector = inspect(engine)
    if _sqlite_courses_need_rebuild(inspector):
        _rebuild_sqlite_courses_table()


def _migrate_postgres() -> None:
    inspector = inspect(engine)
    _ensure_google_id(inspector)

    if "courses" not in inspector.get_table_names():
        return

    columns = _column_names(inspector, "courses")
    with engine.begin() as connection:
        if "schedule_type" not in columns:
            logger.info("Adding missing column 'schedule_type' to 'courses' table...")
            connection.execute(text("ALTER TABLE courses ADD COLUMN schedule_type VARCHAR"))

        if "section" not in columns:
            logger.info("Adding missing column 'section' to 'courses' table...")
            connection.execute(text("ALTER TABLE courses ADD COLUMN section VARCHAR"))

        if "is_listed" not in columns:
            logger.info("Adding missing column 'is_listed' to 'courses' table...")
            connection.execute(text("ALTER TABLE courses ADD COLUMN is_listed BOOLEAN NOT NULL DEFAULT TRUE"))

        connection.execute(text("DROP INDEX IF EXISTS uq_courses_term_crn"))
        connection.execute(text("DROP INDEX IF EXISTS ix_courses_term_listed_code"))
        connection.execute(text("ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_crn_key"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_courses_term_crn ON courses (term_code, crn)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_courses_term_listed_code ON courses (term_code, is_listed, course_code)")
        )


def migrate() -> None:
    """Run lightweight schema migrations needed by the app."""
    logger.info("Starting database migration check...")

    _ensure_app_state_table()

    if engine.dialect.name == "sqlite":
        _migrate_sqlite()
    else:
        _migrate_postgres()

    logger.info("Database migration check complete.")


if __name__ == "__main__":
    migrate()
