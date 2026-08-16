import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  server: {
    port: 9512,
    strictPort: true,
    open: '/',
  },
  preview: {
    port: 9512,
    strictPort: true,
  },
  build: {
    rollupOptions: {
      input: {
        // index 只做語言導向，部署後根路徑才不會 404
        index: resolve(__dirname, 'index.html'),
        landing: resolve(__dirname, 'landing.html'),
        landingEn: resolve(__dirname, 'landing-en.html'),
      },
    },
  },
});
