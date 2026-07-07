"""
services/validation_service.py
================================
The Data Validation Module (Phase 6). Runs BEFORE duplicate detection --
there's no point fuzzy-matching a record whose email field is garbage.

Design: each check is its own small function that returns True/False
("is this value bad?"). `validate_records()` loops every row x every
relevant field x every check, and collects one ValidationLog-shaped dict
per problem found. This makes it trivial to add a new rule later: write
one function, add one line to CHECKS.
"""

import re
from datetime import datetime

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,15}$")
SPECIAL_CHARS_REGEX = re.compile(r"[^a-zA-Z0-9\s.@_\-,]")

# Which field NAMES should trigger which checks. In a real system this
# would be configurable per-upload; hardcoding common field names keeps
# the beginner version understandable.
EMAIL_FIELDS = {"email", "email_address", "e-mail"}
PHONE_FIELDS = {"phone", "phone_number", "mobile", "contact_number"}
DATE_FIELDS = {"date", "dob", "date_of_birth", "created_at", "joining_date"}
ID_FIELDS = {"id", "employee_id", "student_id", "product_id"}


def _is_missing(value) -> bool:
    """Catches None, empty string, and the string 'nan' pandas sometimes produces."""
    return value is None or str(value).strip() == "" or str(value).strip().lower() == "nan"


def _has_extra_spaces(value) -> bool:
    s = str(value)
    return s != s.strip() or "  " in s  # leading/trailing space, or double-space


def _has_special_characters(value) -> bool:
    return bool(SPECIAL_CHARS_REGEX.search(str(value)))


def _is_invalid_email(value) -> bool:
    return not EMAIL_REGEX.match(str(value).strip())


def _is_invalid_phone(value) -> bool:
    digits_only = re.sub(r"\D", "", str(value))
    return not (7 <= len(digits_only) <= 15) or not PHONE_REGEX.match(str(value).strip())


def _is_invalid_date(value) -> bool:
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            datetime.strptime(value, fmt)
            return False
        except ValueError:
            continue
    return True


def validate_records(records: list[dict]) -> list[dict]:
    """
    Runs every applicable check on every record.

    Returns a list of issue dicts:
        [{"row_number": 3, "field_name": "email", "issue_type": "invalid_email", "raw_value": "bob(at)x"}]

    row_number is 1-indexed and counts the HEADER as row 0 conceptually,
    matching what a user sees if they open the file in Excel (row 1 = first data row).
    """
    issues = []

    for i, record in enumerate(records):
        row_number = i + 1

        for field_name, value in record.items():
            field_lower = field_name.strip().lower()

            # --- Universal checks (apply to every field) ---
            if _is_missing(value):
                issues.append(_issue(row_number, field_name, "missing_value", value))
                continue  # no point running other checks on an empty value

            if _has_extra_spaces(value):
                issues.append(_issue(row_number, field_name, "extra_spaces", value))

            if _has_special_characters(value):
                issues.append(_issue(row_number, field_name, "special_characters", value))

            # --- Field-specific checks ---
            if field_lower in EMAIL_FIELDS and _is_invalid_email(value):
                issues.append(_issue(row_number, field_name, "invalid_email", value))

            if field_lower in PHONE_FIELDS and _is_invalid_phone(value):
                issues.append(_issue(row_number, field_name, "invalid_phone", value))

            if field_lower in DATE_FIELDS and _is_invalid_date(value):
                issues.append(_issue(row_number, field_name, "invalid_date", value))

    # --- Duplicate ID / duplicate Name check WITHIN this file ---
    # (Cross-file duplicate detection against the whole database is a
    # separate, more sophisticated job -- see services/dedup_engine/)
    issues.extend(_find_in_file_duplicates(records, ID_FIELDS, "missing_value"))

    return issues


def _issue(row_number, field_name, issue_type, raw_value) -> dict:
    return {
        "row_number": row_number,
        "field_name": field_name,
        "issue_type": issue_type,
        "raw_value": str(raw_value)[:500],  # cap length to avoid absurd TEXT rows
    }


def _find_in_file_duplicates(records: list[dict], id_field_names: set, fallback_issue_type: str) -> list[dict]:
    """
    Flags rows within THIS SAME FILE that repeat an ID field value.
    (Duplicate NAME detection across the whole system is handled by the
    fuzzy/phonetic matchers in the Duplicate Detection Engine, since names
    need similarity matching, not exact matching.)
    """
    seen = {}
    dup_issues = []
    for i, record in enumerate(records):
        row_number = i + 1
        for field_name, value in record.items():
            if field_name.strip().lower() in id_field_names and not _is_missing(value):
                key = (field_name, str(value).strip().lower())
                if key in seen:
                    dup_issues.append(_issue(row_number, field_name, "missing_value", value))
                else:
                    seen[key] = row_number
    return dup_issues


def summarize(issues: list[dict]) -> dict:
    """Small helper for the validation report: counts issues by type."""
    summary = {}
    for issue in issues:
        summary[issue["issue_type"]] = summary.get(issue["issue_type"], 0) + 1
    return summary
