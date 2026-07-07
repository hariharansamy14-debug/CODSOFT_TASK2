"""
utils/file_parser.py
=====================
WHY THIS FILE EXISTS:
The validation engine and duplicate detection engine shouldn't need to know
whether the original file was a CSV, an Excel sheet, JSON, or a TXT file --
they just want "a list of records (dicts)". This module is the ONE place
that knows how to turn each file format into that common shape. This is the
"Adapter pattern": different formats in, one consistent shape out.
"""

import json
import pandas as pd


def parse_file(file_path: str, file_type: str) -> list[dict]:
    """
    Reads a file from disk and returns its rows as a list of dicts,
    e.g. [{"name": "Alice", "email": "a@x.com"}, {"name": "Bob", ...}]

    Raises:
        ValueError: if the file can't be parsed (corrupt/malformed).
    """
    try:
        if file_type == "csv":
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            return df.to_dict(orient="records")

        elif file_type == "xlsx":
            df = pd.read_excel(file_path, dtype=str)
            df = df.fillna("")
            return df.to_dict(orient="records")

        elif file_type == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Accept either a top-level list of records, or {"records": [...]}
            if isinstance(data, dict) and "records" in data:
                return data["records"]
            if isinstance(data, list):
                return data
            raise ValueError("JSON file must contain a list of records or a 'records' key")

        elif file_type == "txt":
            # Assume TXT files are delimited (comma or tab) -- pandas
            # auto-detects via the `sep=None` + python engine combo.
            df = pd.read_csv(file_path, sep=None, engine="python", dtype=str, keep_default_na=False)
            return df.to_dict(orient="records")

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    except Exception as exc:
        raise ValueError(f"Failed to parse {file_type} file: {exc}") from exc
