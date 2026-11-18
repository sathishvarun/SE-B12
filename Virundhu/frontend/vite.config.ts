import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// envDir ".." reads the project-root .env. Only VITE_* variables reach the browser.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: "..",
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: { port: 5450, strictPort: true },
  // The landing page includes the animation library (about 165 kB gzipped in total), so allow a little more.
  build: { chunkSizeWarningLimit: 600 },
});
