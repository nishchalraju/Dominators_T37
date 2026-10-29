import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The FastAPI backend (see backend/README.md) listens on :8000 by default.
// During development the browser only talks to Vite (same origin); Vite forwards
// API calls to the backend, so no CORS or cookies are involved.
const API_TARGET = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'

const apiProxy = {
  '/api': { target: API_TARGET, changeOrigin: true },
  '/docs': { target: API_TARGET, changeOrigin: true },
  '/redoc': { target: API_TARGET, changeOrigin: true },
  '/openapi.json': { target: API_TARGET, changeOrigin: true },
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: true,
    port: 5173,
    // Development convenience (also lets a remote preview host reach the dev server).
    allowedHosts: true,
    proxy: apiProxy,
  },
  preview: {
    host: true,
    port: 4173,
    allowedHosts: true,
    proxy: apiProxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    restoreMocks: true,
  },
})
