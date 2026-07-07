import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api/client";
import DuplicateDiffCard from "../components/DuplicateDiffCard.jsx";

export default function Duplicates() {
  const { fileId } = useParams();
  const [duplicates, setDuplicates] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    const query = statusFilter ? `?status=${statusFilter}` : "";
    api.get(`/duplicates/file/${fileId}${query}`)
      .then((res) => setDuplicates(res.data.data))
      .finally(() => setLoading(false));
  }

  useEffect(load, [fileId, statusFilter]);

  async function handleResolve(duplicateId, action) {
    await api.post(`/duplicates/${duplicateId}/resolve`, { action });
    load();
  }

  async function handleAutoResolve() {
    await api.post(`/duplicates/file/${fileId}/auto-resolve`);
    load();
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 className="display" style={{ fontSize: "1.5rem", marginBottom: 2 }}>Review duplicates</h1>
          <p style={{ color: "var(--slate)", margin: 0, fontSize: "0.9rem" }}>
            The engine flagged these matches — decide what happens to each one.
          </p>
        </div>
        <button className="btn-ink" onClick={handleAutoResolve}>Auto-resolve high confidence</button>
      </div>

      <div className="mb-3">
        {["", "pending", "merged", "replaced", "ignored", "deleted", "kept_latest", "kept_oldest"].map((s) => (
          <button
            key={s}
            className="btn-outline-quiet"
            style={{
              marginRight: 8, marginBottom: 8,
              background: statusFilter === s ? "var(--ink)" : "transparent",
              color: statusFilter === s ? "#fff" : "var(--ink-text)",
            }}
            onClick={() => setStatusFilter(s)}
          >
            {s || "all"}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: "var(--slate)" }}>Loading duplicates…</p>
      ) : duplicates.length === 0 ? (
        <div className="card-surface" style={{ padding: 32, textAlign: "center", color: "var(--slate)" }}>
          No duplicates match this filter.
        </div>
      ) : (
        duplicates.map((d) => (
          <DuplicateDiffCard key={d.id} duplicate={d} onResolve={handleResolve} />
        ))
      )}
    </div>
  );
}
