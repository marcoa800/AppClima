import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // El frontend nunca habla con Open-Meteo, USGS ni eBird directamente:
      // solo con nuestra propia API. Eso mantiene los tokens en el servidor y
      // hace que el cliente de iOS del futuro consuma exactamente lo mismo.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
