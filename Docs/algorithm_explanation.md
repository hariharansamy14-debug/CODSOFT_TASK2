# Algorithm Explanation

This document explains every algorithm used in the Duplicate Detection
Engine (`Backend/app/services/dedup_engine/`), plus Bloom Filters — a
technique the current codebase doesn't use yet, but which is exactly what
you'd reach for if this system needed to scale to millions of records.

## 1. Exact Matching

Normalize two values (lowercase, trim whitespace) and compare with `==`.

- **How**: `normalize(a) == normalize(b)`
- **Time complexity**: O(1) per comparison (after O(k) normalization of a string of length k)
- **Space complexity**: O(1) per comparison; O(n) to index n values for repeated lookups
- **Advantages**: Zero false positives — if it matches, it's genuinely identical (after normalization). Trivial to explain to a non-technical stakeholder.
- **Disadvantages**: Catches nothing that differs by even one character. "Jon" and "John" are treated as completely unrelated.
- **Real-world use**: Employee IDs, SSNs, primary/foreign keys — any field where uniqueness is the whole point of the field.

## 2. Hash-Based Detection (SHA-256 / MD5)

Compute a fixed-length fingerprint of a value (or a whole record) and
compare fingerprints instead of the raw values.

- **How**: `hash(normalize(value))`, compared for equality
- **Time complexity**: O(k) to hash a value of length k; O(1) to compare two hashes
- **Space complexity**: O(n) to store n hashes for fast lookup
- **Advantages**: Lets you compare an ENTIRE record (many fields concatenated) in one O(1) comparison instead of N field comparisons. Also perfect for "have I seen this exact file before?" via a whole-file hash, without re-reading its contents.
- **Disadvantages**: Same fundamental limitation as exact matching — one differing character produces a completely different hash (this is a deliberate cryptographic property called the "avalanche effect"), so it can't catch near-duplicates.
- **SHA-256 vs MD5**: MD5 is faster but has known collision weaknesses (two *different* inputs can produce the same MD5 hash) — acceptable for quick file-identity checks, but SHA-256 is the safer default for anything security-adjacent.
- **Real-world use**: Deduplicating file uploads, detecting tampering, comparing large JSON blobs.

## 3. Levenshtein Distance (Fuzzy Matching)

The minimum number of single-character edits (insertions, deletions,
substitutions) to turn string A into string B, converted to a 0–1
similarity score.

- **Time complexity**: O(n·m) for strings of length n and m (dynamic programming table)
- **Space complexity**: O(n·m) naively, O(min(n,m)) with a rolling-row optimization
- **Advantages**: Excellent for catching typos and minor spelling variations in short strings.
- **Disadvantages**: Ignores word order — "Smith John" scores poorly against "John Smith" despite being the same data, just reordered. Expensive for very long strings.
- **Real-world use**: Person names, product codes, short free-text fields.

## 4. Jaccard Similarity

Treats each string as a SET of word tokens and measures overlap:
`|A ∩ B| / |A ∪ B|`.

- **Time complexity**: O(n + m) to tokenize and compare
- **Space complexity**: O(n + m) for the token sets
- **Advantages**: Doesn't care about word order — "123 Main Street Apt 4" and "Apt 4, 123 Main Street" score identically.
- **Disadvantages**: Treats every word as equally important — "the" counts the same as "Boulevard".
- **Real-world use**: Addresses, multi-word company names, tag/category lists.

## 5. Cosine Similarity (on TF-IDF vectors)

Represents each string as a vector of word-importance scores
(Term Frequency × Inverse Document Frequency) and measures the angle
between two vectors.

- **Time complexity**: O(vocabulary size) to build vectors; O(k) for the dot product
- **Space complexity**: O(vocabulary size)
- **Advantages**: TF-IDF automatically down-weights common words ("the", "street") and up-weights distinctive ones, so it handles longer free text better than Jaccard.
- **Disadvantages**: Needs a reasonable amount of text to be meaningful; overkill for a single short token like a 5-digit ID.
- **Real-world use**: Product descriptions, company names, longer address or bio fields.

## 6. Phonetic Matching (Soundex + Metaphone)

Converts a word into a code representing how it SOUNDS, so words spelled
differently but pronounced similarly produce the same (or similar) code.

- **Soundex**: keeps the first letter, maps remaining consonants into digit
  groups, drops vowels. Example: both "Robert" and "Rupert" → `R163`.
- **Metaphone**: a more modern refinement that better handles English
  pronunciation quirks (silent letters, "ph" → "f", etc.)
- **Time complexity**: O(k) per word — a single pass
- **Space complexity**: O(1) per code
- **Advantages**: Catches "sounds-like" duplicates that spelling-based algorithms miss entirely — e.g., data entered by different people who typed what they heard on a phone call.
- **Disadvantages**: English-specific tuning; can produce false positives on very short names; doesn't help at all for non-name fields.
- **Real-world use**: Customer/patient name matching in call-center and CRM data, where the same person is often spelled multiple different ways across systems.

## 7. Bloom Filters — how this system would scale further

**Not currently implemented** — the engine above is well-suited to the
scale a beginner project (or even a mid-size business) actually needs. But
it's worth understanding, because it's the standard answer once you're
checking a NEW record against tens of millions of EXISTING records, where
even an O(1)-per-comparison hash lookup becomes a lot of memory (storing
every hash of every record).

A Bloom filter is a probabilistic set-membership structure: a fixed-size
bit array plus several hash functions. To check "have I seen this value
before?", you hash the value k different ways, check those k bit
positions — if ALL are set, the value is *probably* already present (with
a small, tunable false-positive rate); if ANY bit is unset, the value is
*definitely* new.

- **Time complexity**: O(k) per lookup/insert, where k = number of hash functions (typically 3–7), independent of how many items are stored
- **Space complexity**: O(m) bits total, where m is chosen based on the expected number of items and your tolerance for false positives — dramatically smaller than storing every actual hash or value
- **Advantages**: Constant-time membership checks with a memory footprint a fraction of storing the real data; ideal as a fast "probably-not-a-duplicate, skip the expensive check" pre-filter in front of the exact/hash/fuzzy pipeline.
- **Disadvantages**: Can produce FALSE POSITIVES (says "might be a duplicate" when it isn't) — never false negatives, so it's safe to use as a first-pass filter, but any "hit" still needs a real exact/hash check to confirm. Can't remove items from a classic Bloom filter (a "Counting Bloom Filter" variant is needed if you need deletions).
- **Real-world use**: The technique behind spell-checkers, network routers checking "have I seen this packet?", and large-scale deduplication systems (e.g., Google Chrome's Safe Browsing list) where you're checking against hundreds of millions of entries and can't afford to store them all in memory.

If this project needed to scale that far, the natural next step would be:
add a Bloom filter in front of `record_store_service.get_existing_records_for_user()`
as a cheap pre-check, only falling through to re-reading and fully comparing
against historical files when the Bloom filter says "possible match".
