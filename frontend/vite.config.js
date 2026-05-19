import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

function copyLegacyStatic() {
  const legacyEntries = [
    "assets",
    "css",
    "js",
    "teacher",
    "student",
    "login.html",
    "register.html"
  ];

  return {
    name: "copy-legacy-static",
    closeBundle() {
      const root = process.cwd();
      const dist = path.join(root, "dist");
      legacyEntries.forEach((entry) => {
        const from = path.join(root, entry);
        const to = path.join(dist, entry);
        if (!fs.existsSync(from)) return;
        fs.cpSync(from, to, { recursive: true, force: true });
      });
    }
  };
}

export default defineConfig({
  plugins: [react(), copyLegacyStatic()],
  server: {
    port: 5173,
    strictPort: false
  },
  preview: {
    port: 4173
  }
});
