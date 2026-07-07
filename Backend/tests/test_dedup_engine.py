"""tests/test_dedup_engine.py -- unit tests for every algorithm in the Duplicate Detection Engine."""

from app.services.dedup_engine import exact_hash_match as ex
from app.services.dedup_engine import fuzzy_match as fz
from app.services.dedup_engine import phonetic_match as ph
from app.services.dedup_engine.engine import detect_duplicates


# --- Exact & Hash matching ---

def test_exact_match_true_for_identical_normalized_values():
    assert ex.exact_match("Bob@Example.com", "  bob@example.com ") is True


def test_exact_match_false_for_different_values():
    assert ex.exact_match("bob@example.com", "alice@example.com") is False


def test_sha256_hash_is_deterministic():
    assert ex.compute_hash("hello") == ex.compute_hash("hello")


def test_sha256_and_md5_produce_different_hashes():
    assert ex.compute_hash("hello", "sha256") != ex.compute_hash("hello", "md5")


# --- Fuzzy matching ---

def test_levenshtein_similarity_high_for_close_typo():
    score = fz.levenshtein_similarity("Jonathan", "Jonathon")
    assert score > 0.8


def test_levenshtein_similarity_low_for_unrelated_strings():
    score = fz.levenshtein_similarity("apple", "zzzzz")
    assert score < 0.3


def test_jaccard_similarity_ignores_word_order():
    score = fz.jaccard_similarity("New York City", "City New York")
    assert score == 1.0  # same set of words


def test_cosine_similarity_identical_strings():
    score = fz.cosine_similarity_score("main street apartment", "main street apartment")
    assert score > 0.99


# --- Phonetic matching ---

def test_soundex_matches_similar_sounding_names():
    assert ph.soundex_match("Robert", "Rupert") is True


def test_metaphone_matches_similar_sounding_names():
    assert ph.metaphone_match("Smith", "Smyth") is True


def test_phonetic_similarity_returns_zero_for_unrelated_names():
    result = ph.phonetic_similarity("Alice", "Zebra")
    assert result["score"] == 0.0


# --- Full engine integration ---

def test_engine_detects_exact_duplicate_email():
    existing = [{"name": "John Smith", "email": "john@example.com"}]
    new = [{"name": "Someone Else", "email": "john@example.com"}]
    findings = detect_duplicates(new, existing)
    assert len(findings) == 1
    assert findings[0]["detection_method"] in ("exact", "sha256")
    assert findings[0]["match_field"] == "email"


def test_engine_detects_phonetic_name_duplicate():
    existing = [{"name": "Catherine Brown", "email": "cat@example.com"}]
    new = [{"name": "Katherine Brown", "email": "different@example.com"}]
    findings = detect_duplicates(new, existing)
    assert len(findings) == 1
    assert findings[0]["match_field"] == "name"


def test_engine_finds_no_duplicate_for_genuinely_different_records():
    existing = [{"name": "John Smith", "email": "john@example.com"}]
    new = [{"name": "Priya Patel", "email": "priya@example.com"}]
    findings = detect_duplicates(new, existing)
    assert len(findings) == 0


def test_engine_catches_duplicate_within_same_batch():
    existing = []
    new = [
        {"name": "Same Person", "email": "same@example.com"},
        {"name": "Same Person", "email": "same@example.com"},
    ]
    findings = detect_duplicates(new, existing)
    assert len(findings) == 1
    assert findings[0]["new_row_number"] == 2  # the SECOND occurrence is the duplicate
