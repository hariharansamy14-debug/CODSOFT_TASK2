import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";

import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import Duplicates from "./pages/Duplicates.jsx";
import Layout from "./components/Layout.jsx";

/**
 * ProtectedRoute
 * ===============
 * Wraps any page that requires login. If auth state is still loading
 * (checking localStorage token on first mount), we render nothing rather
 * than briefly flashing the login page. If there's no user, redirect to
 * /login; otherwise render the requested page inside the shared Layout
 * (sidebar + main content shell).
 */
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload"
        element={
          <ProtectedRoute>
            <UploadPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/duplicates/:fileId"
        element={
          <ProtectedRoute>
            <Duplicates />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
