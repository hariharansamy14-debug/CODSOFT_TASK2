"""
The Duplicate Detection Engine package. `engine.py` is the public entry
point (`detect_duplicates`); the other modules are the individual
algorithms it orchestrates.
"""

from app.services.dedup_engine.engine import detect_duplicates

__all__ = ["detect_duplicates"]
