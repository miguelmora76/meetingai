import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/meetings': 'http://localhost:8000',
      '/incidents': 'http://localhost:8000',
      '/knowledge-base': 'http://localhost:8000',
      '/search': 'http://localhost:8000',
      '/qa': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  build: { outDir: 'dist' },
})
