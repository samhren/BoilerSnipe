"""
Lightweight JSON-backed store for grade distributions.

Loads records from `backend/data/purdue_grades_recent.json` (configurable via
env var GRADES_JSON_PATH) and provides simple query helpers used by the API.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional


DEFAULT_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "purdue_grades_recent.json"


@dataclass
class GradeRecord:
    id: int
    subject: str
    course_number: str
    title: Optional[str]
    academic_period: Optional[str]
    academic_period_desc: Optional[str]
    section: Optional[str]
    crn: Optional[str]
    instructor: Optional[str]
    # Grade percentages
    grade_a_plus: Optional[float] = None
    grade_a: Optional[float] = None
    grade_a_minus: Optional[float] = None
    grade_b_plus: Optional[float] = None
    grade_b: Optional[float] = None
    grade_b_minus: Optional[float] = None
    grade_c_plus: Optional[float] = None
    grade_c: Optional[float] = None
    grade_c_minus: Optional[float] = None
    grade_d_plus: Optional[float] = None
    grade_d: Optional[float] = None
    grade_d_minus: Optional[float] = None
    grade_e: Optional[float] = None
    grade_f: Optional[float] = None
    grade_w: Optional[float] = None
    grade_i: Optional[float] = None
    grade_p: Optional[float] = None
    grade_n: Optional[float] = None
    grade_s: Optional[float] = None
    grade_u: Optional[float] = None
    grade_au: Optional[float] = None
    grade_pi: Optional[float] = None
    grade_si: Optional[float] = None


_lock = RLock()
_records: List[GradeRecord] = []
_by_course: Dict[str, List[GradeRecord]] = {}
_json_mtime: float = 0.0
_json_path: Path = Path(os.getenv("GRADES_JSON_PATH") or DEFAULT_JSON_PATH)


def _load_if_stale():
    global _records, _by_course, _json_mtime
    with _lock:
        if not _json_path.exists():
            _records = []
            _by_course = {}
            _json_mtime = 0.0
            return

        mtime = _json_path.stat().st_mtime
        if mtime == _json_mtime:
            return

        data: List[Dict[str, Any]] = json.loads(_json_path.read_text())

        loaded: List[GradeRecord] = []
        for item in data:
            try:
                # Only accept valid subject/course_number rows
                sub = (item.get('subject') or '').strip()
                num = (item.get('course_number') or '').strip()
                if not sub or not num:
                    continue

                loaded.append(GradeRecord(
                    id=int(item.get('id') or 0),
                    subject=sub,
                    course_number=num,
                    title=item.get('title'),
                    academic_period=item.get('academic_period'),
                    academic_period_desc=item.get('academic_period_desc'),
                    section=item.get('section'),
                    crn=item.get('crn'),
                    instructor=item.get('instructor'),
                    grade_a_plus=item.get('grade_a_plus'),
                    grade_a=item.get('grade_a'),
                    grade_a_minus=item.get('grade_a_minus'),
                    grade_b_plus=item.get('grade_b_plus'),
                    grade_b=item.get('grade_b'),
                    grade_b_minus=item.get('grade_b_minus'),
                    grade_c_plus=item.get('grade_c_plus'),
                    grade_c=item.get('grade_c'),
                    grade_c_minus=item.get('grade_c_minus'),
                    grade_d_plus=item.get('grade_d_plus'),
                    grade_d=item.get('grade_d'),
                    grade_d_minus=item.get('grade_d_minus'),
                    grade_e=item.get('grade_e'),
                    grade_f=item.get('grade_f'),
                    grade_w=item.get('grade_w'),
                    grade_i=item.get('grade_i'),
                    grade_p=item.get('grade_p'),
                    grade_n=item.get('grade_n'),
                    grade_s=item.get('grade_s'),
                    grade_u=item.get('grade_u'),
                    grade_au=item.get('grade_au'),
                    grade_pi=item.get('grade_pi'),
                    grade_si=item.get('grade_si'),
                ))
            except Exception:
                # Skip malformed entries
                continue

        # Index by course key
        by_course: Dict[str, List[GradeRecord]] = {}
        for r in loaded:
            key = f"{r.subject} {r.course_number}"
            by_course.setdefault(key, []).append(r)

        _records = loaded
        _by_course = by_course
        _json_mtime = mtime


def get_by_course(subject: str, course_number: str, instructor: Optional[str] = None) -> List[GradeRecord]:
    _load_if_stale()
    key = f"{subject.upper()} {course_number}"
    records = list(_by_course.get(key, []))
    if instructor:
        inst = instructor.lower()
        records = [r for r in records if r.instructor and inst in r.instructor.lower()]
    return records


def search(subject: Optional[str] = None,
           course_number: Optional[str] = None,
           instructor: Optional[str] = None,
           academic_period: Optional[str] = None,
           limit: int = 50) -> List[GradeRecord]:
    _load_if_stale()
    results: List[GradeRecord] = _records

    if subject:
        s = subject.upper()
        results = [r for r in results if r.subject == s]
    if course_number:
        results = [r for r in results if r.course_number == course_number]
    if instructor:
        inst = instructor.lower()
        results = [r for r in results if r.instructor and inst in r.instructor.lower()]
    if academic_period:
        results = [r for r in results if r.academic_period == academic_period]

    return results[: max(0, limit)]

