"""
services/report_service.py
============================
Generates downloadable reports (Report Module, Phase 11) in three formats.
Each report contains: Duplicates Found, Duplicates Removed, Storage Saved,
Validation Errors, Upload Summary -- exactly what the spec asks for.
"""

import os
import csv
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import xlsxwriter

from app.models import Upload, File, ValidationLog, DuplicateLog


def _gather_report_data(upload_id: int) -> dict:
    upload = Upload.query.get(upload_id)
    files = File.query.filter_by(upload_id=upload_id).all()
    file_ids = [f.id for f in files]

    validation_count = ValidationLog.query.filter(ValidationLog.file_id.in_(file_ids)).count() if file_ids else 0
    duplicate_count = DuplicateLog.query.filter(DuplicateLog.file_id.in_(file_ids)).count() if file_ids else 0
    removed_count = DuplicateLog.query.filter(
        DuplicateLog.file_id.in_(file_ids), DuplicateLog.status.in_(["deleted", "replaced"])
    ).count() if file_ids else 0

    return {
        "upload": upload,
        "files": files,
        "validation_errors": validation_count,
        "duplicates_found": duplicate_count,
        "duplicates_removed": removed_count,
        "storage_saved_bytes": upload.storage_saved_bytes(),
    }


def generate_csv_report(upload_id: int, output_dir: str) -> str:
    data = _gather_report_data(upload_id)
    filename = f"report_upload_{upload_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    path = os.path.join(output_dir, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Upload Name", data["upload"].upload_name])
        writer.writerow(["Total Files", data["upload"].total_files])
        writer.writerow(["Total Records", data["upload"].total_records])
        writer.writerow(["Duplicates Found", data["duplicates_found"]])
        writer.writerow(["Duplicates Removed", data["duplicates_removed"]])
        writer.writerow(["Validation Errors", data["validation_errors"]])
        writer.writerow(["Storage Saved (bytes)", data["storage_saved_bytes"]])

    return path


def generate_excel_report(upload_id: int, output_dir: str) -> str:
    data = _gather_report_data(upload_id)
    filename = f"report_upload_{upload_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(output_dir, filename)

    workbook = xlsxwriter.Workbook(path)
    sheet = workbook.add_worksheet("Summary")
    bold = workbook.add_format({"bold": True})

    sheet.write(0, 0, "Metric", bold)
    sheet.write(0, 1, "Value", bold)
    rows = [
        ("Upload Name", data["upload"].upload_name),
        ("Total Files", data["upload"].total_files),
        ("Total Records", data["upload"].total_records),
        ("Duplicates Found", data["duplicates_found"]),
        ("Duplicates Removed", data["duplicates_removed"]),
        ("Validation Errors", data["validation_errors"]),
        ("Storage Saved (bytes)", data["storage_saved_bytes"]),
    ]
    for i, (label, value) in enumerate(rows, start=1):
        sheet.write(i, 0, label)
        sheet.write(i, 1, value)

    sheet.set_column(0, 1, 30)
    workbook.close()
    return path


def generate_pdf_report(upload_id: int, output_dir: str) -> str:
    data = _gather_report_data(upload_id)
    filename = f"report_upload_{upload_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    path = os.path.join(output_dir, filename)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, "Cloud Deduplication System - Upload Report")

    c.setFont("Helvetica", 11)
    y = height - 100
    lines = [
        f"Upload Name: {data['upload'].upload_name}",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Total Files: {data['upload'].total_files}",
        f"Total Records: {data['upload'].total_records}",
        f"Duplicates Found: {data['duplicates_found']}",
        f"Duplicates Removed: {data['duplicates_removed']}",
        f"Validation Errors: {data['validation_errors']}",
        f"Storage Saved: {data['storage_saved_bytes']} bytes",
    ]
    for line in lines:
        c.drawString(50, y, line)
        y -= 20

    c.save()
    return path
