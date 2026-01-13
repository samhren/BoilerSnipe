"""
Utility to drop the grade_distributions table from the configured database.

Usage:
  python -m scripts.drop_grade_table

Respects DATABASE_URL from backend config. Works for both SQLite and Postgres.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS grade_distributions"))
    print("Dropped table: grade_distributions (if it existed)")


if __name__ == "__main__":
    main()

