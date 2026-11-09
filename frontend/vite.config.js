import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/recharts') || id.includes('/node_modules/d3-')) {
            return 'charts'
          }
          if (id.includes('/node_modules/lucide-react')) {
            return 'icons'
          }
          if (id.includes('/node_modules/react') || id.includes('/node_modules/scheduler')) {
            return 'react-vendor'
          }
        }
      }
    }
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
