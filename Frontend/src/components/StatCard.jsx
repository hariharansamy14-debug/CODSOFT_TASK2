import React from "react";

/**
 * StatCard
 * ========
 * One dashboard metric tile (Total Records, Duplicates Found, etc).
 * `accent` controls the value color ("amber" for duplicate-related
 * numbers, "teal" for clean/unique numbers) so a glance at the dashboard
 * tells you good news (teal) from things needing attention (amber).
 */
export default function StatCard({ label, value, accent }) {
  return (
    <div className="card-surface stat-card">
      <div className="label">{label}</div>
      <div className={`value ${accent || ""}`}>{value}</div>
    </div>
  );
}
