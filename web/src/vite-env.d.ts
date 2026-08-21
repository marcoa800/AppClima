/// <reference types="vite/client" />

/** Variables de entorno que consume el cliente.
 *
 * Sin este fichero, TypeScript no conoce `import.meta.env` y el build falla.
 * Vite lo genera por defecto con `create-vite`, pero este proyecto se montó a
 * mano y se quedó sin él hasta que hizo falta el modo estático.
 */
interface ImportMetaEnv {
  /** 'true' hace que el cliente pida ficheros .json en vez de la API. */
  readonly VITE_API_STATIC?: string
  /** Subdirectorio donde se sirve el sitio. Lo usa vite.config, no el cliente:
   *  el cliente lee `BASE_URL`, que Vite deriva de ahí. */
  readonly VITE_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
