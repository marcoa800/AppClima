import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],

  // GitHub Pages sirve los repos de proyecto en un SUBDIRECTORIO
  // (/AppClima/), no en la raíz del dominio. Sin esto, index.html referencia
  // /assets/... en vez de /AppClima/assets/... y el JavaScript ni siquiera se
  // descarga: la página carga en blanco sin ningún error visible.
  //
  // Se toma de una variable de entorno en lugar de fijar el nombre del repo,
  // para que renombrarlo no rompa el despliegue. El workflow la rellena con el
  // nombre real; en desarrollo queda en '/'.
  base: process.env.VITE_BASE ?? '/',
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
