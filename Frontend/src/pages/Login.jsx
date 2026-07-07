import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1 className="display" style={{ fontSize: "1.4rem", marginBottom: 4 }}>
          Welcome back
        </h1>
        <p style={{ color: "var(--slate)", marginBottom: 24, fontSize: "0.9rem" }}>
          Sign in to your Deduplication Cloud workspace.
        </p>

        {error && (
          <div className="badge-red" style={{ display: "block", padding: "8px 12px", borderRadius: 8, marginBottom: 16, fontFamily: "var(--font-body)", fontWeight: 400 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label" style={{ fontSize: "0.85rem" }}>Email</label>
            <input
              type="email"
              className="form-control"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="mb-4">
            <label className="form-label" style={{ fontSize: "0.85rem" }}>Password</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn-ink w-100" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p style={{ marginTop: 20, fontSize: "0.85rem", color: "var(--slate)", textAlign: "center" }}>
          New here? <Link to="/register" style={{ color: "var(--ink-text)", fontWeight: 600 }}>Create an account</Link>
        </p>
      </div>
    </div>
  );
}
