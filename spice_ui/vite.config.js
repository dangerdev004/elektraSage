import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// /api/* goes to the local ngspice server (pnpm server). Same-origin from the browser's point of view.
const proxy = { '/api': { target: 'http://127.0.0.1:3001', changeOrigin: false } };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
});
