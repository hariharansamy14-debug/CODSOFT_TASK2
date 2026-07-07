import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load, if a token already exists (page refresh), fetch the
  // profile to restore the logged-in state instead of forcing a re-login.
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/profile")
      .then((res) => setUser(res.data.data))
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const res = await api.post("/auth/login", { email, password });
    const { user, access_token, refresh_token } = res.data.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    setUser(user);
    return user;
  }

  async function register(full_name, email, password) {
    await api.post("/auth/register", { full_name, email, password });
    return login(email, password);
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook so components do `const { user } = useAuth()` instead of
// importing useContext + AuthContext everywhere.
export function useAuth() {
  return useContext(AuthContext);
}
