import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip,
} from "chart.js";
import api from "../api/client";
import StatCard from "../components/StatCard.jsx";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let value = bytes;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  return `${value.toFixed(1)} ${units[i]}`;
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [trend, setTrend] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/dashboard/summary"),
      api.get("/dashboard/upload-history"),
      api.get("/dashboard/duplicate-trend"),
    ])
      .then(([s, h, t]) => {
        setSummary(s.data.data);
        setHistory(h.data.data);
        setTrend(t.data.data);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "var(--slate)" }}>Loading dashboard…</p>;

  const chartData = {
    labels: trend.map((t) => t.detection_method),
    datasets: [
      {
        label: "Duplicates found",
        data: trend.map((t) => t.count),
        backgroundColor: "#E8A33D",
        borderRadius: 4,
      },
    ],
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 className="display" style={{ fontSize: "1.5rem", marginBottom: 2 }}>Dashboard</h1>
          <p style={{ color: "var(--slate)", margin: 0, fontSize: "0.9rem" }}>
            An overview of your uploads, duplicates, and storage savings.
          </p>
        </div>
        <Link to="/upload" className="btn-ink">+ New upload</Link>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-3"><StatCard label="Uploaded Files" value={summary.total_uploaded_files} /></div>
        <div className="col-md-3"><StatCard label="Total Records" value={summary.total_records} /></div>
        <div className="col-md-3"><StatCard label="Duplicates Found" value={summary.duplicate_records} accent="amber" /></div>
        <div className="col-md-3"><StatCard label="Unique Records" value={summary.unique_records} accent="teal" /></div>
      </div>

      <div className="row g-3">
        <div className="col-md-4">
          <div className="card-surface" style={{ padding: 20 }}>
            <div className="label" style={{ fontSize: "0.78rem", textTransform: "uppercase", color: "var(--slate)", marginBottom: 10 }}>
              Storage Saved
            </div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: "1.6rem", fontWeight: 700, color: "var(--teal)" }}>
              {formatBytes(summary.storage_saved_bytes)}
            </div>
            <p style={{ color: "var(--slate)", fontSize: "0.82rem", marginTop: 8 }}>
              Estimated space not spent storing duplicate records.
            </p>
          </div>
        </div>

        <div className="col-md-8">
          <div className="card-surface" style={{ padding: 20 }}>
            <div className="label" style={{ fontSize: "0.78rem", textTransform: "uppercase", color: "var(--slate)", marginBottom: 10 }}>
              Duplicates by Detection Method
            </div>
            {trend.length === 0 ? (
              <p style={{ color: "var(--slate)", fontSize: "0.85rem" }}>No duplicates detected yet.</p>
            ) : (
              <Bar data={chartData} options={{ plugins: { legend: { display: false } }, responsive: true }} height={90} />
            )}
          </div>
        </div>
      </div>

      <div className="card-surface mt-4" style={{ padding: 20 }}>
        <div className="label" style={{ fontSize: "0.78rem", textTransform: "uppercase", color: "var(--slate)", marginBottom: 14 }}>
          Recent Uploads
        </div>
        {history.length === 0 ? (
          <p style={{ color: "var(--slate)", fontSize: "0.85rem" }}>No uploads yet — start by uploading your first file.</p>
        ) : (
          <table className="table" style={{ marginBottom: 0 }}>
            <thead>
              <tr style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--slate)" }}>
                <th>Upload</th><th>Files</th><th>Records</th><th>Duplicates</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((u) => (
                <tr key={u.id} style={{ fontSize: "0.88rem" }}>
                  <td>{u.upload_name}</td>
                  <td>{u.total_files}</td>
                  <td>{u.total_records}</td>
                  <td>{u.duplicate_records > 0 ? <span className="badge-soft badge-amber">{u.duplicate_records}</span> : "0"}</td>
                  <td><span className={`badge-soft ${u.status === "completed" ? "badge-teal" : "badge-neutral"}`}>{u.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
