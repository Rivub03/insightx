// vite.config.js
//
// PURPOSE:
//   Vite build tool configuration.
//   Two jobs here:
//     1. Register the React plugin so Vite can process .jsx files
//     2. Set up a dev-server proxy so API calls reach the FastAPI backend
//
// WHY THE PROXY?
//   In development, React runs on http://localhost:5173 and FastAPI runs on
//   http://localhost:8000. API calls in the code use relative URLs like
//   /api/v1/datasources — without a proxy, the browser would send those
//   to localhost:5173/api/... which does not exist.
//
//   The proxy intercepts any request starting with /api and forwards it to
//   FastAPI on port 8000. The browser never knows the backend is on a
//   different port. This is only active during `npm run dev` — in production
//   you handle this at the web server level (nginx, etc.).

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,  // The port your browser opens. Change if 5173 is taken.
    proxy: {
      // Any request whose path starts with /api is forwarded to FastAPI
      '/api': {
        target:       'http://localhost:8000',  // Your FastAPI backend
        changeOrigin: true,                     // Rewrites the Host header
      },
    },
  },
})
