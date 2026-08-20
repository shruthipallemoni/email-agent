import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite is the tool that runs our React app during development
// (fast reload every time we save a file) and builds it for production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
