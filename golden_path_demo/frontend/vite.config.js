import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/adstackr': {
        target: 'http://3.144.250.88:8000',
        changeOrigin: true,
	secure: false
      },
      '/google': {
        target: 'http://3.148.238.101:8000',
        changeOrigin: true,
      },
    },
  },
})

