"""
services/dedup_engine/fuzzy_match.py
=====================================
Exact and hash matching only catch duplicates that are IDENTICAL after
normalization. But real-world duplicate data is messy: "Jon Smith" vs
"John Smith", or "123 Main St, Apt 4" vs "123 Main Street Apartment 4".
Fuzzy matching estimates how SIMILAR two values are, from 0.0 (nothing
alike) to 1.0 (identical), so we can catch near-duplicates too.

ALGORITHM 3: Levenshtein Distance (edit distance)
--------------------------------------------------
Counts the minimum number of single-character edits (insert/delete/
substitute) needed to turn string A into string B. We convert that raw
edit count into a 0-1 SIMILARITY score by dividing by the longer string's
length: similarity = 1 - (edit_distance / max_len).

    Time complexity:  O(n*m) where n, m are the two strings' lengths
                       (classic dynamic-programming edit-distance table).
    Space complexity: O(n*m) naively, O(min(n,m)) with a rolling-row
                       optimization (what python-Levenshtein's C code does).
    Best for: short strings with typos -- names, product codes.
    Weakness: doesn't understand WORD order ("John Smith" vs "Smith John"
              scores poorly despite being the same person).

ALGORITHM 4: Jaccard Similarity
---------------------------------
Treats each string as a SET of tokens (words, or overlapping character
n-grams) and measures overlap: |A ∩ B| / |A ∪ B|.

    Time complexity:  O(n + m) to build sets and compute the intersection.
    Space complexity: O(n + m) for the token sets.
    Best for: multi-word fields like addresses, where word ORDER
              shouldn't matter as much as which words are shared.
    Weakness: ignores word order entirely and doesn't weigh "important"
              vs "common" words differently.

ALGORITHM 5: Cosine Similarity (on TF-IDF vectors)
----------------------------------------------------
Represents each string as a vector of word-importance scores (TF-IDF:
Term Frequency - Inverse Document Frequency) and measures the angle
between two vectors: cos(theta) = (A . B) / (|A| * |B|).

    Time complexity:  O(vocabulary size) to build vectors, O(k) to compute
                       the dot product where k = vector dimensionality.
    Space complexity: O(vocabulary size) for the TF-IDF matrix.
    Best for: longer free-text fields (descriptions, addresses, company
              names) where some words matter more than others -- TF-IDF
              naturally down-weights common words like "the" or "street".
    Weakness: needs a reasonable amount of text to be meaningful; overkill
              for single short tokens like a 5-digit ID.
"""

import Levenshtein
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity


def levenshtein_similarity(value_a: str, value_b: str) -> float:
    """Algorithm 3: Levenshtein Distance, converted to a 0-1 similarity score."""
    a, b = str(value_a).strip().lower(), str(value_b).strip().lower()
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    distance = Levenshtein.distance(a, b)
    return 1 - (distance / max_len)


def jaccard_similarity(value_a: str, value_b: str) -> float:
    """Algorithm 4: Jaccard Similarity over word tokens."""
    tokens_a = set(str(value_a).strip().lower().split())
    tokens_b = set(str(value_b).strip().lower().split())
    if not tokens_a and not tokens_b:
        return 1.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union) if union else 0.0


def cosine_similarity_score(value_a: str, value_b: str) -> float:
    """Algorithm 5: Cosine Similarity over TF-IDF vectors."""
    a, b = str(value_a).strip().lower(), str(value_b).strip().lower()
    if not a or not b:
        return 1.0 if a == b else 0.0
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([a, b])
        score = sk_cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(score)
    except ValueError:
        # Happens if both strings are made ENTIRELY of stopword-like tokens
        # that TfidfVectorizer discards, leaving an empty vocabulary.
        return 1.0 if a == b else 0.0


def best_fuzzy_score(value_a: str, value_b: str) -> dict:
    """
    Runs all three fuzzy algorithms and returns the strongest signal, along
    with which method produced it -- useful because different algorithms
    suit different field types (see module docstring above).
    """
    scores = {
        "levenshtein": levenshtein_similarity(value_a, value_b),
        "jaccard": jaccard_similarity(value_a, value_b),
        "cosine": cosine_similarity_score(value_a, value_b),
    }
    best_method = max(scores, key=scores.get)
    return {"method": best_method, "score": scores[best_method], "all_scores": scores}
