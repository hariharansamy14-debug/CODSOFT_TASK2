/**
 * api/client.js
 * ==============
 * One shared axios instance for every API call in the app. Two jobs:
 *
 * 1. Automatically attaches the JWT access token to every outgoing
 *    request, so individual components never have to remember to do it.
 * 2. Automatically tries to REFRESH an expired access token (using the
 *    refresh token) and retries the original request -- so a user isn't
 *    logged out just because their 30-minute access token expired mid-session.
 */

import axios from "axios";

const api = axios.create({
  baseURL: "/api", // proxied to the Flask backend, see vite.config.js / nginx.conf
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let pendingQueue = [];

function resolvePendingQueue(error, token = null) {
  pendingQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)));
  pendingQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt a refresh once per request, and only on a 401 that
    // ISN'T from the refresh/login endpoints themselves (avoids infinite loops).
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes("/auth/login") &&
      !originalRequest.url.includes("/auth/refresh")
    ) {
      if (isRefreshing) {
        // Another request already triggered a refresh -- wait for it
        // instead of firing a second refresh call.
        return new Promise((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        const { data } = await axios.post(
          "/api/auth/refresh",
          {},
          { headers: { Authorization: `Bearer ${refreshToken}` } }
        );
        const newToken = data.data.access_token;
        localStorage.setItem("access_token", newToken);
        resolvePendingQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        resolvePendingQueue(refreshError, null);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
