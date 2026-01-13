"""
Build a consolidated JSON of recent Purdue grade distributions from CSV exports
and normalize fields for API consumption.

Usage:
  python -m scripts.build_recent_grades_json \
    --input-dir . \
    --output backend/data/purdue_grades_recent.json

Expects CSVs named like:
  "grades.xlsx - Spring 2025.csv"
  "grades.xlsx - Fall 2024.csv"

The script tolerates both single-row and stacked-row headers where grade columns
appear as "% of Total" in the header row and the letter grade lives in the row
above it (e.g., A, A-, B+, ...).
If no CSVs are found, it will fall back to parsing a single Excel file named
"grades.xlsx" in --input-dir, reading all sheets.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd


# Default list of recent semester files
DEFAULT_FILES = [
    "grades.xlsx - Spring 2025.csv", "grades.xlsx - Fall 2024.csv",
    "grades.xlsx - Spring 2024.csv", "grades.xlsx - Fall 2023.csv",
    "grades.xlsx - Summer 2023.csv", "grades.xlsx - Spring 2023.csv",
    "grades.xlsx - Fall 2022.csv", "grades.xlsx - Summer 2022.csv",
    "grades.xlsx - Spring 2022.csv", "grades.xlsx - Fall 2021.csv",
]


GRADE_FIELD_MAP: Dict[str, str] = {
    "A+": "grade_a_plus",
    "A": "grade_a",
    "A-": "grade_a_minus",
    "B+": "grade_b_plus",
    "B": "grade_b",
    "B-": "grade_b_minus",
    "C+": "grade_c_plus",
    "C": "grade_c",
    "C-": "grade_c_minus",
    "D+": "grade_d_plus",
    "D": "grade_d",
    "D-": "grade_d_minus",
    "E": "grade_e",
    "F": "grade_f",
    "W": "grade_w",
    "I": "grade_i",
    "P": "grade_p",
    "N": "grade_n",
    "S": "grade_s",
    "U": "grade_u",
    "AU": "grade_au",
    "PI": "grade_pi",
    "SI": "grade_si",
}


def process_csv(file_path: Path) -> List[Dict[str, Any]]:
    # Load raw CSV with no headers
    df_raw = pd.read_csv(file_path, header=None)

    # Find the header row index where column 0 equals "Subject"
    subj_rows = df_raw[df_raw[0] == "Subject"].index
    if len(subj_rows) == 0:
        return []

    subj_idx = subj_rows[0]
    header_row = df_raw.iloc[subj_idx]
    grade_row = df_raw.iloc[subj_idx - 1] if subj_idx - 1 >= 0 else pd.Series([])

    # Map headers to handle both single-row and stacked-row formats
    cols: List[str] = []
    for i in range(len(header_row)):
        val = str(header_row[i]).strip()
        top = str(grade_row[i]).strip() if i < len(grade_row) else "nan"

        if i < 9:  # Columns: Subject through Instructor (stable leading set)
            cols.append(val)
        else:
            label = top if top != "nan" else val
            if val == "% of Total":
                cols.append(f"{label}_pct")
            elif val == "Students":
                cols.append(f"{label}_count")
            else:
                cols.append(label)

    # Load data with derived headers
    df = pd.read_csv(file_path, skiprows=subj_idx + 1, header=None).iloc[:, : len(cols)]
    df.columns = cols

    # Forward-fill course metadata
    meta_cols = ['Subject', 'Course Number', 'Title', 'Academic Period Desc']
    for mc in meta_cols:
        if mc in df.columns:
            df[mc] = df[mc].ffill()

    # Filter to real section rows
    df = df.dropna(subset=['Section']) if 'Section' in df.columns else df

    # Convert to dict records
    records = df.to_dict(orient='records')

    # Normalize into API-friendly fields (snake_case with grade_* keys)
    normalized: List[Dict[str, Any]] = []
    for rec in records:
        base = {
            'subject': str(rec.get('Subject', '')).strip(),
            'course_number': str(rec.get('Course Number', '')).strip(),
            'title': (str(rec.get('Title')).strip() if pd.notna(rec.get('Title')) else None),
            'academic_period': str(rec.get('Academic Period', '')).strip() if 'Academic Period' in rec else None,
            'academic_period_desc': (str(rec.get('Academic Period Desc')).strip() if pd.notna(rec.get('Academic Period Desc')) else None),
            'section': str(rec.get('Section')).strip() if pd.notna(rec.get('Section')) else None,
            'crn': str(rec.get('CRN')).strip() if pd.notna(rec.get('CRN')) else None,
            'instructor': str(rec.get('Instructor')).strip() if pd.notna(rec.get('Instructor')) else None,
        }

        # Attach grade percentages where available (0.0-1.0 expected)
        for letter, fieldname in GRADE_FIELD_MAP.items():
            pct_key = f"{letter}_pct"
            if pct_key in rec and pd.notna(rec[pct_key]):
                try:
                    val = float(rec[pct_key])
                    if 0.0 <= val <= 1.0:
                        base[fieldname] = val
                except (ValueError, TypeError):
                    pass

        normalized.append(base)

    return normalized


def find_header_row(df_raw: pd.DataFrame) -> Optional[int]:
    for idx in range(min(15, len(df_raw))):
        if str(df_raw.iloc[idx, 0]) == 'Subject':
            return idx
    return None


def process_excel_sheet(df_raw: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
    header_row = find_header_row(df_raw)
    if header_row is None:
        return []

    headers = list(df_raw.iloc[header_row])

    # Handle stacked headers ("% of Total" under letter grade row)
    if '% of Total' in headers and header_row - 1 >= 0:
        grade_row = list(df_raw.iloc[header_row - 1])
        new_headers = []
        for i, h in enumerate(headers):
            if h == '% of Total' and i < len(grade_row) and pd.notna(grade_row[i]):
                new_headers.append(str(grade_row[i]).strip())
            else:
                new_headers.append(h)
        headers = new_headers

    df = df_raw.iloc[header_row + 1 :].copy()
    df.columns = headers

    # Forward fill key descriptors
    for col in ['Subject', 'Subject Desc', 'Course Number', 'Title', 'Academic Period Desc']:
        if col in df.columns:
            df[col] = df[col].ffill()

    # Remove empty rows
    if 'Academic Period' in df.columns:
        df = df[df['Academic Period'].notna()]
    if 'Section' in df.columns:
        df = df[df['Section'].notna()]

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        rec = {
            'subject': str(row.get('Subject', '')).strip() if pd.notna(row.get('Subject')) else None,
            'course_number': str(row.get('Course Number', '')).strip() if pd.notna(row.get('Course Number')) else None,
            'title': str(row.get('Title', '')).strip() if pd.notna(row.get('Title')) else None,
            'academic_period': str(row.get('Academic Period', '')).strip() if pd.notna(row.get('Academic Period')) else None,
            'academic_period_desc': str(row.get('Academic Period Desc', '')).strip() if pd.notna(row.get('Academic Period Desc')) else None,
            'section': str(row.get('Section', '')).strip() if pd.notna(row.get('Section')) else None,
            'crn': str(row.get('CRN', '')).strip() if pd.notna(row.get('CRN')) else None,
            'instructor': str(row.get('Instructor', '')).strip() if pd.notna(row.get('Instructor')) else None,
        }

        if not rec['subject'] or not rec['course_number'] or not rec['academic_period']:
            continue

        # Attach grade percentages from columns that match letter names
        for letter, fieldname in GRADE_FIELD_MAP.items():
            if letter in df.columns:
                value = row.get(letter)
                if pd.notna(value):
                    try:
                        val = float(value)
                        if 0.0 <= val <= 1.0:
                            rec[fieldname] = val
                    except (ValueError, TypeError):
                        pass

        records.append(rec)

    return records


def main():
    parser = argparse.ArgumentParser(description="Build consolidated recent grades JSON")
    parser.add_argument("--input-dir", default=".", help="Directory containing CSV files")
    parser.add_argument("--output", default="backend/data/purdue_grades_recent.json", help="Output JSON path")
    parser.add_argument("--files", nargs="*", default=DEFAULT_FILES, help="Explicit CSV filenames to include")
    parser.add_argument("--subject-summary-output", default=None, help="Optional path to write per-subject averages JSON")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_records: List[Dict[str, Any]] = []
    # Prefer CSVs if present
    found_csv = False
    for fname in args.files:
        fpath = input_dir / fname
        if fpath.exists():
            found_csv = True
            all_records.extend(process_csv(fpath))

    # Fallback: parse Excel workbook if no CSVs found
    if not found_csv:
        xlsx_path = input_dir / 'grades.xlsx'
        if xlsx_path.exists():
            xlsx = pd.ExcelFile(xlsx_path)
            for sheet in xlsx.sheet_names:
                df_raw = pd.read_excel(xlsx, sheet_name=sheet, header=None)
                all_records.extend(process_excel_sheet(df_raw, sheet))

    # Assign synthetic IDs for compatibility with API schema
    for i, rec in enumerate(all_records, start=1):
        rec['id'] = i

    with out_path.open('w') as f:
        json.dump(all_records, f, indent=2)

    print(f"Wrote {len(all_records)} records to {out_path}")

    # Optional: write subject-level averages
    if args.subject_summary_output:
        by_subject: Dict[str, Dict[str, Any]] = {}
        grade_keys = list(GRADE_FIELD_MAP.values())
        for rec in all_records:
            subj = rec.get('subject')
            if not subj:
                continue
            agg = by_subject.setdefault(subj, {
                'subject': subj,
                'sections': 0,
                **{k: [] for k in grade_keys},
            })
            agg['sections'] += 1
            for k in grade_keys:
                v = rec.get(k)
                if isinstance(v, (int, float)):
                    agg[k].append(float(v))

        # Average values
        out_list: List[Dict[str, Any]] = []
        for subj, agg in by_subject.items():
            out_item: Dict[str, Any] = {'subject': subj, 'sections': agg['sections']}
            for k in grade_keys:
                vals = agg[k]
                out_item[k] = sum(vals) / len(vals) if vals else None
            out_list.append(out_item)

        ss_path = Path(args.subject_summary_output)
        ss_path.parent.mkdir(parents=True, exist_ok=True)
        with ss_path.open('w') as sf:
            json.dump(out_list, sf, indent=2)
        print(f"Wrote subject summary for {len(out_list)} subjects to {ss_path}")


if __name__ == "__main__":
    main()
