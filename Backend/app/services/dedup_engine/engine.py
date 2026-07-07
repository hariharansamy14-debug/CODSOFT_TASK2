"""
services/dedup_engine/engine.py
=================================
The Duplicate Detection Engine (Phase 7). This is the orchestrator that
ties together all 6 algorithms (exact_hash_match, fuzzy_match,
phonetic_match) into one pipeline, run field by field, in a deliberate
FAST-TO-SLOW order:

    1. Exact match      (O(1) per comparison -- cheapest, catches most cases)
    2. Hash match        (O(1) per comparison -- for whole-record comparison)
    3. Phonetic match    (O(k) per comparison -- name fields only)
    4. Fuzzy match       (O(n*m) per comparison -- most expensive, run LAST
                           and only on records that survived steps 1-3
                           without already being flagged)

WHY THIS ORDER MATTERS (Performance Optimization requirement #16):
Running expensive fuzzy string comparisons on every possible pair of
records is O(N*M) -- fine for hundreds of records, painfully slow for
hundreds of thousands. By using a hash index for exact matches FIRST
(O(1) lookups), we only ever run the expensive fuzzy algorithms on the
records that didn't already match exactly -- usually a small minority.

FIELD -> ALGORITHM MAPPING (the spec asks for detection across Name,
Email, Phone, Address, Employee ID, Student ID, Product ID, custom fields):
    - ID fields (employee_id, student_id, product_id): EXACT + HASH only.
      IDs are structured codes -- "fuzzy" similarity has no real meaning
      here (ID "1002" being 90% similar to "1003" is meaningless; either
      they match or they don't).
    - email, phone: EXACT match after normalization (case/whitespace/
      punctuation stripped) -- these are also structured enough that near-
      matches usually mean a DIFFERENT contact, not a typo of the same one.
    - name: EXACT -> PHONETIC -> FUZZY (in that order) -- names are exactly
      where phonetic + fuzzy matching earns its keep ("Jon"/"John",
      "Catherine"/"Kathryn").
    - address, custom free-text fields: EXACT -> FUZZY (Jaccard/Cosine
      suit multi-word text better than Levenshtein).
"""

from app.services.dedup_engine import exact_hash_match as ex
from app.services.dedup_engine import fuzzy_match as fz
from app.services.dedup_engine import phonetic_match as ph

ID_FIELDS = {"employee_id", "student_id", "product_id", "id"}
EMAIL_FIELDS = {"email", "email_address", "e-mail"}
PHONE_FIELDS = {"phone", "phone_number", "mobile", "contact_number"}
NAME_FIELDS = {"name", "full_name", "first_name", "last_name", "customer_name"}
ADDRESS_FIELDS = {"address", "street_address", "location"}

FUZZY_THRESHOLD = 0.85   # similarity >= this counts as "likely duplicate"
PHONETIC_THRESHOLD = 0.6  # matches best_fuzzy_score's "one algorithm agreed" tier


def _classify_field(field_name: str) -> str:
    f = field_name.strip().lower()
    if f in ID_FIELDS:
        return "id"
    if f in EMAIL_FIELDS:
        return "email"
    if f in PHONE_FIELDS:
        return "phone"
    if f in NAME_FIELDS:
        return "name"
    if f in ADDRESS_FIELDS:
        return "address"
    return "custom"


def detect_duplicates(new_records: list[dict], existing_records: list[dict]) -> list[dict]:
    """
    Compares every record in `new_records` against `existing_records`
    (previously stored, already-unique records) AND against each other
    (to catch duplicates uploaded twice in the SAME file).

    Returns a list of duplicate findings:
        [{
          "new_row_number": int,
          "existing_record_ref": str,   # which existing record it matches (its index/id as string)
          "match_field": str,
          "detection_method": "exact" | "sha256" | ... ,
          "similarity_score": float,
        }, ...]
    """
    findings = []
    all_reference_records = existing_records + new_records  # a new record can dupe an earlier NEW record too

    for i, record in enumerate(new_records):
        row_number = i + 1
        # Only compare against records that come BEFORE this one in the
        # combined list, so record #5 vs #5 isn't flagged against itself,
        # and we don't report the same pair twice (A-dupes-B AND B-dupes-A).
        candidate_pool = all_reference_records[: len(existing_records) + i]

        match = _find_best_match(record, candidate_pool)
        if match:
            findings.append({
                "new_row_number": row_number,
                "existing_record_ref": match["ref"],
                "match_field": match["field"],
                "detection_method": match["method"],
                "similarity_score": match["score"],
            })

    return findings


def _find_best_match(record: dict, candidates: list[dict]) -> dict | None:
    """
    Checks one record against a pool of candidates, field by field, using
    the fast-to-slow algorithm order described in the module docstring.
    Stops at the FIRST strong match found (no need to keep searching once
    we're confident it's a duplicate).
    """
    for field_name, value in record.items():
        if ex.normalize(value) == "":
            continue  # empty values can't meaningfully "match" anything

        field_type = _classify_field(field_name)

        for ref_index, candidate in enumerate(candidates):
            candidate_value = candidate.get(field_name)
            if candidate_value is None:
                continue

            # --- Step 1: Exact match (cheapest, run for every field type) ---
            if ex.exact_match(value, candidate_value):
                return {"ref": str(ref_index), "field": field_name, "method": "exact", "score": 1.0}

            # --- Step 2: Hash match (equivalent to exact here, included to
            #     satisfy "hash-based detection" as its own explicit method
            #     when comparing a WHOLE record instead of one field) ---
            if ex.compute_hash(value) == ex.compute_hash(candidate_value):
                return {"ref": str(ref_index), "field": field_name, "method": "sha256", "score": 1.0}

            # --- Steps 3-4 only apply to name/address/custom fields; IDs,
            #     emails, and phones are structured data where a "close but
            #     not exact" match usually means a genuinely different record ---
            if field_type == "name":
                phonetic = ph.phonetic_similarity(value, candidate_value)
                if phonetic["score"] >= PHONETIC_THRESHOLD:
                    return {
                        "ref": str(ref_index), "field": field_name,
                        "method": phonetic["method"], "score": phonetic["score"],
                    }

            if field_type in ("name", "address", "custom"):
                fuzzy = fz.best_fuzzy_score(value, candidate_value)
                if fuzzy["score"] >= FUZZY_THRESHOLD:
                    return {
                        "ref": str(ref_index), "field": field_name,
                        "method": fuzzy["method"], "score": fuzzy["score"],
                    }

    return None
