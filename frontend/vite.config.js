import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// 将 /api 请求代理到后端，避免前端开发时跨域问题
export default defineConfig(({ mode }) => {
  // 读取项目根目录的 .env（frontend 的上一级）
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')

  const frontendPort = parseInt(env.FRONTEND_PORT || '5173', 10)
  const backendPort  = parseInt(env.BACKEND_PORT  || '8000', 10)

  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
