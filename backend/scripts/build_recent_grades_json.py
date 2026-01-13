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
import re

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

# Match header cells that indicate a percentage column under a grade label row
PERCENT_HEADER_RE = re.compile(r"^(%|pct|percent(?:age)?)\s*of\s*total\b", re.IGNORECASE)

# Match a composite header like "A % of Total" or "B- Percent of Total"
COMPOSITE_GRADE_HEADER_RE = re.compile(
    r"^(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|E|F|W|I|P|N|S|U|AU|PI|SI)\b.*",
    re.IGNORECASE,
)


def find_header_row(df_raw: pd.DataFrame) -> Optional[int]:
    max_scan = min(80, len(df_raw))
    for idx in range(max_scan):
        row_vals = [str(v).strip().lower() for v in list(df_raw.iloc[idx])]
        if any(v == 'subject' or v.startswith('subject') for v in row_vals):
            return idx
    return None


def _normalize_grade_code(s: str) -> Optional[str]:
    if not s:
        return None
    t = str(s).strip().upper().replace(" ", "")
    # Normalize common variants like 'A +' -> 'A+'
    t = t.replace("A+", "A+").replace("A-", "A-")
    # Exact matches
    if t in GRADE_FIELD_MAP:
        return t
    # Extract from composite header like 'A % of Total'
    m = COMPOSITE_GRADE_HEADER_RE.match(t)
    if m:
        code = m.group(1).upper()
        # Normalize spacing already removed; ensure valid
        return code if code in GRADE_FIELD_MAP else None
    return None


def process_excel_sheet(df_raw: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
    # Skip the problematic summary sheet requested by user
    if sheet_name.strip().lower() == 'sum16-sum21':
        return []

    header_row = find_header_row(df_raw)
    if header_row is None:
        return []

    headers = [str(h).strip() for h in list(df_raw.iloc[header_row])]

    # Handle stacked headers (percent indicator under letter grade row)
    # Be flexible: match '% of Total', 'Percent of Total', 'Pct of Total', etc.
    if header_row - 1 >= 0:
        grade_row = list(df_raw.iloc[header_row - 1])
        new_headers = []
        for i, h in enumerate(headers):
            h_str = str(h).strip()
            if PERCENT_HEADER_RE.match(h_str):
                # Try to pull the grade label from the same index, else look back 1-2 cols
                grade_label = None
                # Candidates: i, i-1, i-2
                for j in (i, i - 1, i - 2):
                    if 0 <= j < len(grade_row) and pd.notna(grade_row[j]):
                        grade_label = str(grade_row[j]).strip()
                        if grade_label:
                            break
                new_headers.append(grade_label or h_str)
            else:
                new_headers.append(h_str)
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

    # Build a mapping of recognized grade columns from headers
    grade_columns: Dict[str, str] = {}
    for col in df.columns:
        code = _normalize_grade_code(col)
        if code and code not in grade_columns:
            grade_columns[code] = col

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

        # Attach grade percentages using detected grade columns
        for letter, fieldname in GRADE_FIELD_MAP.items():
            colname = grade_columns.get(letter)
            if colname is None:
                continue
            value = row.get(colname)
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
