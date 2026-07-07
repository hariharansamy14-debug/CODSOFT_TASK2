"""
services/storage_service.py
============================
WHY THIS FILE EXISTS:
The rest of the app (upload routes, dedup engine) should never need to know
or care whether a file physically lives on the local disk or in an AWS S3
bucket. This module hides that decision behind two functions: `save_file()`
and `delete_file()`. Today `Config.STORAGE_BACKEND == "local"`, so files go
to `./storage/uploads`. Later, flipping one env var to `STORAGE_BACKEND=s3`
(with AWS credentials filled in) switches every upload to S3 -- ZERO changes
needed anywhere else in the codebase. This is the "Strategy pattern": one
interface, swappable implementations.
"""

import os
import uuid
from datetime import datetime
from flask import current_app


def _generate_unique_filename(original_filename: str) -> str:
    """
    Builds a collision-proof filename: <timestamp>_<uuid4-hex>.<ext>
    WHY: two different users could both upload "data.csv" at the same
    second. A UUID makes a collision astronomically unlikely.
    """
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex
    return f"{timestamp}_{unique_id}.{ext}" if ext else f"{timestamp}_{unique_id}"


def save_file(file_storage, subfolder: str = "") -> dict:
    """
    Saves an uploaded file (a Flask `FileStorage` object) using whichever
    backend is configured, and returns metadata about where it landed.

    Returns:
        {
          "stored_filename": str,
          "storage_path": str,     # local path OR s3 key
          "storage_type": "local" | "s3",
          "file_size_bytes": int,
        }
    """
    stored_filename = _generate_unique_filename(file_storage.filename)
    backend = current_app.config["STORAGE_BACKEND"]

    if backend == "s3":
        return _save_to_s3(file_storage, stored_filename, subfolder)
    return _save_to_local(file_storage, stored_filename, subfolder)


def _save_to_local(file_storage, stored_filename: str, subfolder: str) -> dict:
    base_path = current_app.config["LOCAL_STORAGE_PATH"]
    target_dir = os.path.join(base_path, subfolder) if subfolder else base_path
    os.makedirs(target_dir, exist_ok=True)

    full_path = os.path.join(target_dir, stored_filename)
    file_storage.save(full_path)
    file_size = os.path.getsize(full_path)

    return {
        "stored_filename": stored_filename,
        "storage_path": full_path,
        "storage_type": "local",
        "file_size_bytes": file_size,
    }


def _save_to_s3(file_storage, stored_filename: str, subfolder: str) -> dict:
    """
    S3 implementation -- inactive until STORAGE_BACKEND=s3 and AWS
    credentials are supplied. Kept here, fully written, so switching
    backends later is a config change, not a rewrite.
    """
    import boto3  # imported lazily -- boto3 isn't needed at all while local-only

    s3 = boto3.client(
        "s3",
        aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
        region_name=current_app.config["AWS_REGION"],
    )
    key = f"{subfolder}/{stored_filename}" if subfolder else stored_filename
    bucket = current_app.config["AWS_S3_BUCKET"]

    file_storage.stream.seek(0, os.SEEK_END)
    file_size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    s3.upload_fileobj(file_storage.stream, bucket, key)

    return {
        "stored_filename": stored_filename,
        "storage_path": key,
        "storage_type": "s3",
        "file_size_bytes": file_size,
    }


def delete_file(storage_path: str, storage_type: str) -> None:
    """Removes a stored file from whichever backend holds it."""
    if storage_type == "s3":
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
            region_name=current_app.config["AWS_REGION"],
        )
        s3.delete_object(Bucket=current_app.config["AWS_S3_BUCKET"], Key=storage_path)
    else:
        if os.path.exists(storage_path):
            os.remove(storage_path)


def read_file_bytes(storage_path: str, storage_type: str) -> bytes:
    """Reads a stored file's raw bytes back out, regardless of backend."""
    if storage_type == "s3":
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
            region_name=current_app.config["AWS_REGION"],
        )
        obj = s3.get_object(Bucket=current_app.config["AWS_S3_BUCKET"], Key=storage_path)
        return obj["Body"].read()
    with open(storage_path, "rb") as f:
        return f.read()
