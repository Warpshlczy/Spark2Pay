import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Frontend talks to the Flask backend through this dev proxy
      // (backend/.env sets PORT=3040 on this machine; default is 3038)
      '/api': {
        target: process.env.BACKEND_ORIGIN || 'http://localhost:3038',
        changeOrigin: true
      }
    }
  }
})
