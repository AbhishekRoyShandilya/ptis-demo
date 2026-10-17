import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so the built site works from any path (GitHub Pages project URL or a custom domain)
export default defineConfig({ plugins: [react()], base: "./" });
