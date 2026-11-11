import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      // The API listens on 127.0.0.1:5080 (docker-compose api port). changeOrigin stays false so the
      // Host header is the panel's own address; the API sees the same origin as the browser (cookie session).
      '/api': { target: 'http://127.0.0.1:5080', changeOrigin: false },
    },
  },
  preview: { host: '127.0.0.1', port: 5174, strictPort: true },
});
