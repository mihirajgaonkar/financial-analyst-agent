import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8001",
      "/research": "http://127.0.0.1:8001",
      "/companies": "http://127.0.0.1:8001",
      "/chat": "http://127.0.0.1:8001",
      "/threads": "http://127.0.0.1:8001"
    }
  }
});
