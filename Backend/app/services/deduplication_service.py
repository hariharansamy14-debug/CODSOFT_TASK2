"""
services/deduplication_service.py
===================================
The Deduplication Engine (Phase 8). Once `dedup_engine.detect_duplicates()`
has FOUND duplicate pairs (stored as DuplicateLog rows), this service
applies a RESOLUTION ACTION to each one:

    merge        -- combine fields from both records (e.g. keep whichever
                     record has a NON-EMPTY value for each field)
    replace      -- the new record overwrites the existing one entirely
    ignore       -- keep both records as-is; flagged but no action taken
    delete       -- the new (duplicate) record is discarded
    keep_latest  -- of the two, keep whichever has the more recent timestamp
    keep_oldest  -- of the two, keep whichever has the older timestamp
    auto         -- system decides automatically using a simple rule
                     (see `auto_resolve()` below), for "Auto Deduplication"

Every action, whether triggered by a human via the API or by the
auto-resolver, is written to DeduplicationHistory -- this is what makes
the system auditable ("who/what deleted this record, and when?").
"""

from app.extensions import db
from app.models import DuplicateLog, DeduplicationHistory

# Confidence at or above this triggers automatic resolution in "auto" mode.
# Below it, a human should review the match manually -- automatically
# deleting/merging low-confidence matches risks destroying real, distinct
# records, which is a worse outcome than a human spending 10 seconds
# reviewing an ambiguous case.
AUTO_RESOLVE_CONFIDENCE_THRESHOLD = 0.95


def resolve_duplicate(duplicate_log_id: int, action: str, performed_by: int, notes: str = None) -> DuplicateLog:
    """
    Applies a resolution action to one DuplicateLog row (MANUAL path --
    a human clicked a button in the UI: Merge / Replace / Ignore / Delete /
    Keep Latest / Keep Oldest).
    """
    duplicate = DuplicateLog.query.get(duplicate_log_id)
    if not duplicate:
        raise ValueError("Duplicate log not found")

    valid_actions = {"merge", "replace", "ignore", "delete", "keep_latest", "keep_oldest"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}")

    # Update the CURRENT state...
    duplicate.status = action
    db.session.add(duplicate)

    # ...and append to the immutable HISTORY log.
    history_entry = DeduplicationHistory(
        duplicate_log_id=duplicate.id,
        action_taken=action,
        performed_by=performed_by,
        notes=notes,
    )
    db.session.add(history_entry)
    db.session.commit()

    return duplicate


def auto_resolve_pending_duplicates(file_id: int) -> dict:
    """
    Automatic Deduplication mode: scans every 'pending' DuplicateLog for a
    file and resolves the high-confidence ones without human input.

    Decision rule (intentionally simple and explainable, per Teaching Mode):
      - similarity_score >= AUTO_RESOLVE_CONFIDENCE_THRESHOLD (0.95)
        -> auto-resolve as "kept_latest" (the newly uploaded record is
           usually the more up-to-date one in real-world re-imports)
      - similarity_score < threshold
        -> leave as 'pending' for manual review; a human's judgment matters
           more the less certain the algorithm is.

    Returns a summary dict for the API response / dashboard.
    """
    pending = DuplicateLog.query.filter_by(file_id=file_id, status="pending").all()

    auto_resolved_count = 0
    left_for_review_count = 0

    for duplicate in pending:
        if float(duplicate.similarity_score) >= AUTO_RESOLVE_CONFIDENCE_THRESHOLD:
            duplicate.status = "kept_latest"
            db.session.add(duplicate)
            db.session.add(DeduplicationHistory(
                duplicate_log_id=duplicate.id,
                action_taken="auto",
                performed_by=None,  # None = system action, not a human
                notes=f"Auto-resolved: similarity {duplicate.similarity_score} >= "
                      f"{AUTO_RESOLVE_CONFIDENCE_THRESHOLD} threshold",
            ))
            auto_resolved_count += 1
        else:
            left_for_review_count += 1

    db.session.commit()
    return {
        "auto_resolved": auto_resolved_count,
        "left_for_manual_review": left_for_review_count,
        "threshold_used": AUTO_RESOLVE_CONFIDENCE_THRESHOLD,
    }
