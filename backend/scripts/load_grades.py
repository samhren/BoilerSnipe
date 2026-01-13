"""
Script to load grade distribution data from grades.xlsx into the database.
Run with: python -m scripts.load_grades
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import GradeDistribution, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Column mapping from Excel headers to model fields
GRADE_COLUMN_MAP = {
    'A+': 'grade_a_plus',
    'A': 'grade_a',
    'A-': 'grade_a_minus',
    'B+': 'grade_b_plus',
    'B': 'grade_b',
    'B-': 'grade_b_minus',
    'C+': 'grade_c_plus',
    'C': 'grade_c',
    'C-': 'grade_c_minus',
    'D+': 'grade_d_plus',
    'D': 'grade_d',
    'D-': 'grade_d_minus',
    'E': 'grade_e',
    'F': 'grade_f',
    'W': 'grade_w',
    'I': 'grade_i',
    'P': 'grade_p',
    'N': 'grade_n',
    'S': 'grade_s',
    'U': 'grade_u',
    'AU': 'grade_au',
    'PI': 'grade_pi',
    'SI': 'grade_si',
}


def find_header_row(df_raw):
    """Find the row index containing 'Subject' header."""
    for idx in range(min(15, len(df_raw))):
        if df_raw.iloc[idx, 0] == 'Subject':
            return idx
    return None


def process_sheet(df_raw, sheet_name: str):
    """Process a single sheet and return list of record dicts."""
    header_row = find_header_row(df_raw)
    if header_row is None:
        logger.warning(f"Could not find header row in sheet '{sheet_name}', skipping")
        return []

    # Get the headers
    headers = list(df_raw.iloc[header_row])

    # Check if we have "% of Total" columns (need to get grade letters from row above)
    if '% of Total' in headers:
        # Get grade letters from row above
        grade_row = list(df_raw.iloc[header_row - 1])
        # Build new headers combining grade letters where needed
        new_headers = []
        for i, h in enumerate(headers):
            if h == '% of Total' and i < len(grade_row) and pd.notna(grade_row[i]):
                new_headers.append(str(grade_row[i]).strip())
            else:
                new_headers.append(h)
        headers = new_headers

    # Create dataframe with proper headers
    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = headers

    # Check required columns
    required = ['Subject', 'Course Number', 'Academic Period']
    for req in required:
        if req not in df.columns:
            logger.warning(f"Missing required column '{req}' in sheet '{sheet_name}', skipping")
            return []

    # Forward fill grouped columns
    fill_cols = ['Subject', 'Subject Desc', 'Course Number', 'Title']
    for col in fill_cols:
        if col in df.columns:
            df[col] = df[col].ffill()

    # Filter out rows without academic period (empty/header rows)
    df = df[df['Academic Period'].notna()]

    # Filter out rows without section or CRN
    if 'Section' in df.columns:
        df = df[df['Section'].notna()]
    elif 'CRN' in df.columns:
        df = df[df['CRN'].notna()]

    records = []
    for _, row in df.iterrows():
        try:
            record_data = {
                'subject': str(row.get('Subject', '')).strip() if pd.notna(row.get('Subject')) else None,
                'course_number': str(row.get('Course Number', '')).strip() if pd.notna(row.get('Course Number')) else None,
                'title': str(row.get('Title', '')).strip() if pd.notna(row.get('Title')) else None,
                'academic_period': str(row.get('Academic Period', '')).strip() if pd.notna(row.get('Academic Period')) else None,
                'academic_period_desc': str(row.get('Academic Period Desc', '')).strip() if pd.notna(row.get('Academic Period Desc')) else None,
                'section': str(row.get('Section', '')).strip() if pd.notna(row.get('Section')) else None,
                'crn': str(row.get('CRN', '')).strip() if pd.notna(row.get('CRN')) else None,
                'instructor': str(row.get('Instructor', '')).strip() if pd.notna(row.get('Instructor')) else None,
            }

            # Skip if missing required fields
            if not record_data['subject'] or not record_data['course_number'] or not record_data['academic_period']:
                continue

            # Add grade percentages
            for excel_name, model_field in GRADE_COLUMN_MAP.items():
                if excel_name in df.columns:
                    value = row.get(excel_name)
                    if pd.notna(value):
                        try:
                            float_val = float(value)
                            if 0 <= float_val <= 1:
                                record_data[model_field] = float_val
                        except (ValueError, TypeError):
                            pass

            records.append(record_data)
        except Exception as e:
            logger.warning(f"Error processing row: {e}")
            continue

    return records


def load_grades(xlsx_path: str = 'grades.xlsx', clear_existing: bool = False):
    """Main function to load all grade data."""
    logger.info(f"Loading grades from {xlsx_path}")

    # Ensure table exists
    Base.metadata.create_all(bind=engine)

    # Read all sheets
    logger.info("Reading Excel file...")
    xlsx = pd.ExcelFile(xlsx_path)

    db = SessionLocal()
    try:
        if clear_existing:
            logger.info("Clearing existing grade data...")
            deleted = db.query(GradeDistribution).delete()
            db.commit()
            logger.info(f"  Deleted {deleted} existing records")

        total_records = 0
        for sheet_name in xlsx.sheet_names:
            logger.info(f"Processing sheet: {sheet_name}")
            df_raw = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
            records = process_sheet(df_raw, sheet_name)

            if records:
                # Bulk insert in batches to avoid timeouts
                batch_size = 500
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    db.bulk_insert_mappings(GradeDistribution, batch)
                    db.commit()
                    if i > 0 and i % 5000 == 0:
                        logger.info(f"    ... {i}/{len(records)} inserted")

            logger.info(f"  Inserted {len(records)} records")
            total_records += len(records)

        logger.info(f"Total records inserted: {total_records}")

    finally:
        db.close()

    return total_records


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Load grade distribution data')
    parser.add_argument('--clear', action='store_true', help='Clear existing data before loading')
    parser.add_argument('--file', default='grades.xlsx', help='Path to Excel file')
    args = parser.parse_args()

    load_grades(args.file, args.clear)
