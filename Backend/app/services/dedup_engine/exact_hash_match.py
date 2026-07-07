"""
services/dedup_engine/exact_hash_match.py
==========================================
ALGORITHM 1: Exact Matching
----------------------------
The simplest possible duplicate check: normalize two values (lowercase,
strip whitespace) and compare with `==`. If they're identical, it's a
duplicate with 100% confidence.

    Time complexity:  O(1) per comparison, O(n) to check one record
                       against n existing records (or O(1) with a hash
                       set/index, which is what we do below).
    Space complexity: O(n) to store the set of seen values.
    Use case: employee IDs, email addresses, SSNs -- fields where ANY
              difference means a genuinely different entity.

ALGORITHM 2: Hash-Based Detection (SHA-256 / MD5)
--------------------------------------------------
Instead of comparing a value directly, we compute a cryptographic hash of
it (or of a whole normalized record) and compare HASHES. This is really
just exact matching "in disguise" -- two identical inputs always produce
the identical hash -- but it's extremely useful for:
  1. Comparing a WHOLE RECORD (all fields concatenated) in one comparison
     instead of field-by-field.
  2. Detecting "have I seen this exact file before?" via a whole-file hash
     (see File.checksum_sha256 in the database schema) without re-reading
     every row.

    Why SHA-256 over MD5: MD5 is faster but has known collision
    vulnerabilities (two different inputs CAN produce the same MD5 hash).
    We default to SHA-256 for correctness and offer MD5 for speed-critical
    cases or for matching legacy systems that only store MD5 hashes.
    Time complexity:  O(k) to hash a string of length k; O(1) to compare
                       two hashes.
    Space complexity: O(n) to store n hashes in a lookup set.
"""

import hashlib


def normalize(value: str) -> str:
    """Lowercase + strip whitespace so 'Bob@X.com' and ' bob@x.com ' match."""
    return str(value).strip().lower()


def exact_match(value_a: str, value_b: str) -> bool:
    """Algorithm 1: Exact Matching."""
    return normalize(value_a) == normalize(value_b)


def compute_hash(value: str, algorithm: str = "sha256") -> str:
    """
    Algorithm 2: Hash-Based Detection.
    Hashes a normalized value (or a whole record's concatenated fields).
    """
    normalized = normalize(value).encode("utf-8")
    if algorithm == "md5":
        return hashlib.md5(normalized).hexdigest()
    return hashlib.sha256(normalized).hexdigest()


def record_hash(record: dict, fields: list[str], algorithm: str = "sha256") -> str:
    """
    Hashes an entire record by concatenating the given fields in a fixed
    order. Used to detect "this whole row is identical to one already in
    the system" in a single comparison, rather than N field comparisons.
    """
    concatenated = "|".join(normalize(record.get(f, "")) for f in fields)
    return compute_hash(concatenated, algorithm)


def build_hash_index(existing_values: list[str], algorithm: str = "sha256") -> dict:
    """
    Pre-computes hashes for every EXISTING record's value once, so checking
    N new records against M existing records is O(N + M) instead of O(N*M).
    Returns {hash: original_value}.
    """
    return {compute_hash(v, algorithm): v for v in existing_values}
