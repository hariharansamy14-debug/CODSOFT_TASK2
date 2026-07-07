import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await register(fullName, email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || "Registration failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1 className="display" style={{ fontSize: "1.4rem", marginBottom: 4 }}>
          Create your account
        </h1>
        <p style={{ color: "var(--slate)", marginBottom: 24, fontSize: "0.9rem" }}>
          Start detecting and removing duplicate data in minutes.
        </p>

        {error && (
          <div className="badge-red" style={{ display: "block", padding: "8px 12px", borderRadius: 8, marginBottom: 16, fontFamily: "var(--font-body)", fontWeight: 400 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label" style={{ fontSize: "0.85rem" }}>Full name</label>
            <input className="form-control" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="mb-3">
            <label className="form-label" style={{ fontSize: "0.85rem" }}>Email</label>
            <input type="email" className="form-control" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="mb-4">
            <label className="form-label" style={{ fontSize: "0.85rem" }}>Password</label>
            <input type="password" className="form-control" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <div style={{ fontSize: "0.75rem", color: "var(--slate)", marginTop: 4 }}>At least 8 characters.</div>
          </div>
          <button type="submit" className="btn-ink w-100" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p style={{ marginTop: 20, fontSize: "0.85rem", color: "var(--slate)", textAlign: "center" }}>
          Already have an account? <Link to="/login" style={{ color: "var(--ink-text)", fontWeight: 600 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
