import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// WHY A PROXY: during local development, the React dev server runs on
// :5173 and the Flask API on :5000 -- different "origins", which browsers
// block by default (CORS). Rather than relying only on Flask-CORS, this
// proxy makes the browser think everything is served from ONE origin,
// exactly matching how nginx does it in production (see Docker/nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
