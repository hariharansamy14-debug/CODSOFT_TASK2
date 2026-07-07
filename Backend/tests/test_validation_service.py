"""tests/test_validation_service.py -- unit tests for the Data Validation Module."""

from app.services.validation_service import validate_records, summarize


def test_detects_missing_value():
    records = [{"name": "Alice", "email": ""}]
    issues = validate_records(records)
    assert any(i["issue_type"] == "missing_value" for i in issues)


def test_detects_invalid_email():
    records = [{"name": "Bob", "email": "not-an-email"}]
    issues = validate_records(records)
    assert any(i["issue_type"] == "invalid_email" for i in issues)


def test_valid_email_passes():
    records = [{"name": "Bob", "email": "bob@example.com"}]
    issues = validate_records(records)
    assert not any(i["issue_type"] == "invalid_email" for i in issues)


def test_detects_invalid_phone():
    records = [{"name": "Carl", "phone": "abc"}]
    issues = validate_records(records)
    assert any(i["issue_type"] == "invalid_phone" for i in issues)


def test_detects_extra_spaces():
    records = [{"name": "  Dana  ", "email": "dana@example.com"}]
    issues = validate_records(records)
    assert any(i["issue_type"] == "extra_spaces" and i["field_name"] == "name" for i in issues)


def test_detects_invalid_date():
    records = [{"name": "Eve", "date": "not-a-date"}]
    issues = validate_records(records)
    assert any(i["issue_type"] == "invalid_date" for i in issues)


def test_valid_date_passes():
    records = [{"name": "Eve", "date": "2024-01-15"}]
    issues = validate_records(records)
    assert not any(i["issue_type"] == "invalid_date" for i in issues)


def test_summarize_counts_by_type():
    issues = [
        {"issue_type": "missing_value"}, {"issue_type": "missing_value"}, {"issue_type": "invalid_email"},
    ]
    summary = summarize(issues)
    assert summary["missing_value"] == 2
    assert summary["invalid_email"] == 1
