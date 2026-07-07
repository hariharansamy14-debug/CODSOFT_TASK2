import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

const ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls", "json", "txt"];

export default function UploadPage() {
  const [files, setFiles] = useState([]);
  const [uploadName, setUploadName] = useState("");
  const [isDragActive, setIsDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  function addFiles(newFiles) {
    const valid = Array.from(newFiles).filter((f) => {
      const ext = f.name.split(".").pop().toLowerCase();
      return ALLOWED_EXTENSIONS.includes(ext);
    });
    setFiles((prev) => [...prev, ...valid]);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragActive(false);
    addFiles(e.dataTransfer.files);
  }

  function removeFile(index) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setError(null);
    setResult(null);
    setUploading(true);
    setProgress(0);

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    if (uploadName) formData.append("upload_name", uploadName);

    try {
      const res = await api.post("/uploads", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          setProgress(Math.round((evt.loaded * 100) / evt.total));
        },
      });
      setResult(res.data.data);
      setFiles([]);
    } catch (err) {
      setError(err.response?.data?.error || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <h1 className="display" style={{ fontSize: "1.5rem", marginBottom: 2 }}>Upload data</h1>
      <p style={{ color: "var(--slate)", marginBottom: 24, fontSize: "0.9rem" }}>
        Drop CSV, Excel, JSON, or TXT files. We'll validate them and check for duplicates automatically.
      </p>

      <div className="card-surface" style={{ padding: 24, marginBottom: 20 }}>
        <div className="mb-3">
          <label className="form-label" style={{ fontSize: "0.85rem" }}>Upload name (optional)</label>
          <input
            className="form-control"
            placeholder="e.g. March Payroll Import"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
          />
        </div>

        <div
          className={`dropzone ${isDragActive ? "active" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragActive(true); }}
          onDragLeave={() => setIsDragActive(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".csv,.xlsx,.xls,.json,.txt"
            style={{ display: "none" }}
            onChange={(e) => addFiles(e.target.files)}
          />
          <div style={{ fontSize: "1.6rem", marginBottom: 8 }}>📂</div>
          <div style={{ fontWeight: 600, color: "var(--ink-text)" }}>Drag files here, or click to browse</div>
          <div style={{ fontSize: "0.8rem", marginTop: 4 }}>Supports .csv, .xlsx, .json, .txt — multiple files allowed</div>
        </div>

        {files.length > 0 && (
          <ul style={{ listStyle: "none", padding: 0, marginTop: 16, marginBottom: 0 }}>
            {files.map((f, i) => (
              <li key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "var(--paper)", borderRadius: 8, marginBottom: 6, fontSize: "0.85rem" }}>
                <span>{f.name} <span style={{ color: "var(--slate)" }}>({(f.size / 1024).toFixed(1)} KB)</span></span>
                <button className="btn-outline-quiet" style={{ padding: "2px 10px" }} onClick={() => removeFile(i)}>Remove</button>
              </li>
            ))}
          </ul>
        )}

        {uploading && (
          <div className="progress mt-3" style={{ height: 8 }}>
            <div className="progress-bar" role="progressbar" style={{ width: `${progress}%`, background: "var(--amber)" }} />
          </div>
        )}

        {error && (
          <div style={{ marginTop: 16, padding: "10px 14px", background: "var(--red-soft)", color: "var(--red)", borderRadius: 8, fontSize: "0.85rem" }}>
            {error}
          </div>
        )}

        <button
          className="btn-ink mt-3"
          disabled={files.length === 0 || uploading}
          onClick={handleUpload}
        >
          {uploading ? `Uploading… ${progress}%` : `Upload ${files.length || ""} file${files.length === 1 ? "" : "s"}`}
        </button>
      </div>

      {result && (
        <div className="card-surface" style={{ padding: 24 }}>
          <div className="label" style={{ fontSize: "0.78rem", textTransform: "uppercase", color: "var(--slate)", marginBottom: 14 }}>
            Upload complete
          </div>
          <div className="row g-3 mb-3">
            <div className="col-md-4"><strong>{result.upload.total_records}</strong> records processed</div>
            <div className="col-md-4"><span className="badge-soft badge-amber">{result.upload.duplicate_records}</span> duplicates found</div>
            <div className="col-md-4"><span className="badge-soft badge-teal">{result.upload.unique_records}</span> unique records</div>
          </div>
          <table className="table">
            <thead>
              <tr style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--slate)" }}>
                <th>File</th><th>Records</th><th>Validation issues</th><th>Duplicates</th><th></th>
              </tr>
            </thead>
            <tbody>
              {result.files.map((f, i) => (
                <tr key={i} style={{ fontSize: "0.88rem" }}>
                  <td>{f.filename}</td>
                  <td>{f.record_count ?? "—"}</td>
                  <td>{f.validation_issues ?? 0}</td>
                  <td>{f.duplicates_found ?? 0}</td>
                  <td>
                    {f.duplicates_found > 0 && (
                      <button className="btn-outline-quiet" onClick={() => navigate(`/duplicates/${f.file_id}`)}>
                        Review
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
