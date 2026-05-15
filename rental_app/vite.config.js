import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_PROXY_TARGET =
  process.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8000";

export default defineConfig(({ mode }) => {
  if (mode === "production" && !(process.env.VITE_API_BASE_URL || "").trim()) {
    console.warn(
      "[RentalAI] VITE_API_BASE_URL is unset for production build. " +
        "AI Chat will call /api/ai-chat on the static host (fails on Render Static Site). " +
        "Set VITE_API_BASE_URL in Render Dashboard → Environment before npm run build.",
    );
  }

  return {
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
  };
});
