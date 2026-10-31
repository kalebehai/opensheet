import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@shared": fileURLToPath(new URL("../shared/types", import.meta.url)) },
  },
  server: {
    port: 5173,
    host: true,
    fs: { allow: [".."] },
  },
});
