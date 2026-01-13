"""
Build a consolidated JSON of recent Purdue grade distributions directly from
the Excel workbook (grades.xlsx), normalizing fields for API consumption.

Usage:
  python -m scripts.build_recent_grades_json \
    --file grades.xlsx \
    --output backend/data/purdue_grades_recent.json

Notes:
- Handles both single-row and stacked-row headers where grade columns appear as
  "% of Total" with letter grades in the previous row (A, A-, B+, ...).
- Skips the "Sum16-Sum21" sheet per request.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd


# No CSV support; we always parse the Excel workbook


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


def _normalize_grade_value(v: Any) -> Optional[float]:
    """Return a 0-1 float for grade share, or None if invalid.

    Accepts:
    - decimals in [0,1]
    - percents in (1, 100] which are divided by 100
    - strings with trailing '%'
    """
    if pd.isna(v):
        return None
    try:
        if isinstance(v, str):
            s = v.strip()
            if s.endswith('%'):
                s = s[:-1].strip()
                num = float(s)
                return max(0.0, min(1.0, num / 100.0))
            num = float(s)
        else:
            num = float(v)
        if 0.0 <= num <= 1.0:
            return num
        if 1.0 < num <= 100.0:
            return num / 100.0
    except (ValueError, TypeError):
        return None
    return None


# CSV processing removed per request


def find_header_row(df_raw: pd.DataFrame) -> Optional[int]:
    max_scan = min(50, len(df_raw))
    for idx in range(max_scan):
        cell = str(df_raw.iloc[idx, 0]).strip().lower()
        if cell == 'subject' or 'subject' in cell:
            return idx
    return None


def process_excel_sheet(df_raw: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
    # Skip the problematic summary sheet requested by user
    if sheet_name.strip().lower() == 'sum16-sum21':
        return []

    header_row = find_header_row(df_raw)
    if header_row is None:
        return []

    headers = [str(h).strip() for h in list(df_raw.iloc[header_row])]

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
    df.columns = [str(h).strip() for h in headers]

    # Forward fill key descriptors
    for col in ['Subject', 'Subject Desc', 'Course Number', 'Title', 'Academic Period', 'Academic Period Desc']:
        if col in df.columns:
            df[col] = df[col].ffill()

    # Remove clearly empty rows; be lenient about missing academic period/section
    if 'Subject' in df.columns:
        df = df[df['Subject'].notna()]

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

        # Require minimal keys only to avoid dropping rows from variant tables
        if not rec['subject'] or not rec['course_number']:
            continue

        # Attach grade percentages from columns that match letter names
        for letter, fieldname in GRADE_FIELD_MAP.items():
            if letter in df.columns:
                value = row.get(letter)
                val = _normalize_grade_value(value)
                if val is not None:
                    rec[fieldname] = val

        records.append(rec)

    return records


def main():
    parser = argparse.ArgumentParser(description="Build consolidated recent grades JSON from Excel workbook")
    parser.add_argument("--file", default="grades.xlsx", help="Path to grades.xlsx workbook")
    parser.add_argument("--output", default="backend/data/purdue_grades_recent.json", help="Output JSON path")
    parser.add_argument("--subject-summary-output", default=None, help="Optional path to write per-subject averages JSON")
    args = parser.parse_args()

    xlsx_path = Path(args.file)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not xlsx_path.exists():
        raise FileNotFoundError(f"Excel workbook not found: {xlsx_path}")

    all_records: List[Dict[str, Any]] = []
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
