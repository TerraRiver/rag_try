import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 将 /api 请求代理到后端，避免前端开发时跨域问题
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
