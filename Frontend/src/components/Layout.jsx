import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/upload", label: "Upload", icon: "⬆️" },
];

export default function Layout({ children }) {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span>DeDupe</span>
          <span className="dot">Cloud</span>
        </div>

        {NAV_ITEMS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`sidebar-link ${location.pathname === item.to ? "active" : ""}`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}

        <div style={{ marginTop: "auto", paddingTop: 24 }}>
          <div style={{ fontSize: "0.8rem", color: "#8a8fa3", marginBottom: 8 }}>
            {user?.full_name}
          </div>
          <button className="sidebar-link" style={{ width: "100%", border: "none", background: "none", cursor: "pointer" }} onClick={logout}>
            <span>🚪</span>
            <span>Log out</span>
          </button>
        </div>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
}
