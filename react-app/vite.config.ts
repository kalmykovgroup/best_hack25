import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // Production optimizations
  build: {
    // Папка для сборки (будет обслуживаться ASP.NET Core)
    outDir: '../api/wwwroot',
    emptyOutDir: true,

    // Генерируем source maps для отладки в production (можно отключить)
    sourcemap: true,

    // Оптимизация chunk splitting
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor библиотеки в отдельный chunk
          vendor: ['react', 'react-dom', 'react-redux'],
          redux: ['@reduxjs/toolkit'],
          signalr: ['@microsoft/signalr'],
        },
      },
    },

    // Минификация
    minify: 'terser',
    terserOptions: {
      compress: {
        // Удаляем console.* в production (кроме console.error)
        drop_console: true,
        drop_debugger: true,
      },
    },

    // Размер chunk warning (500kb)
    chunkSizeWarningLimit: 500,
  },

  // Server configuration
  server: {
    port: 5174,
  },

  // Preview configuration (для production preview)
  preview: {
    port: 5174,
  },
})
