"""
services/dedup_engine/phonetic_match.py
=========================================
ALGORITHM 6: Phonetic Matching (Soundex + Metaphone)
------------------------------------------------------
Fuzzy matching (Levenshtein etc.) compares SPELLING. But "Catherine" and
"Kathryn" are spelled quite differently, edit-distance-wise, yet SOUND
almost identical -- a very common real-world source of duplicate person
records. Phonetic algorithms convert a word into a code representing how
it SOUNDS, so two names that sound alike produce the same (or a similar)
code even if spelled differently.

Soundex: the classic algorithm (used by the US Census since 1930!). Keeps
the first letter, then maps remaining consonants to digit groups
(labials, gutturals, etc.) and drops vowels, producing a code like "K350".

Metaphone: a more modern, more accurate refinement of Soundex that handles
English pronunciation rules better (e.g. silent letters, "ph" -> "f").

    Time complexity:  O(k) per name, where k = name length (single pass).
    Space complexity: O(1) per code (fixed-length or short output).
    Best for: person names, especially across data entered by different
              people who spelled what they HEARD ("Meagan" vs "Megan").
    Weakness: language-specific (tuned for English pronunciation), and
              can produce false positives for short names.
"""

import jellyfish


def soundex_match(value_a: str, value_b: str) -> bool:
    """Algorithm 6a: Soundex -- True if both values produce the same phonetic code."""
    a, b = str(value_a).strip(), str(value_b).strip()
    if not a or not b:
        return a == b
    return jellyfish.soundex(a) == jellyfish.soundex(b)


def metaphone_match(value_a: str, value_b: str) -> bool:
    """Algorithm 6b: Metaphone -- generally more accurate than Soundex for English names."""
    a, b = str(value_a).strip(), str(value_b).strip()
    if not a or not b:
        return a == b
    return jellyfish.metaphone(a) == jellyfish.metaphone(b)


def phonetic_similarity(value_a: str, value_b: str) -> dict:
    """
    Combines both phonetic checks into one confidence signal:
      - both match       -> 1.0  (strong phonetic duplicate signal)
      - one matches       -> 0.6  (weaker, but still worth flagging)
      - neither matches    -> 0.0
    """
    soundex_hit = soundex_match(value_a, value_b)
    metaphone_hit = metaphone_match(value_a, value_b)

    if soundex_hit and metaphone_hit:
        score = 1.0
    elif soundex_hit or metaphone_hit:
        score = 0.6
    else:
        score = 0.0

    method = "soundex" if soundex_hit and not metaphone_hit else "metaphone"
    return {"method": method, "score": score, "soundex_match": soundex_hit, "metaphone_match": metaphone_hit}
