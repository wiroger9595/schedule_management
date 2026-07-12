import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  server: {
    port: 9512,
    strictPort: true,
    open: '/landing.html',
  },
  preview: {
    port: 9512,
    strictPort: true,
  },
  build: {
    rollupOptions: {
      input: {
        landing: resolve(__dirname, 'landing.html'),
        landingEn: resolve(__dirname, 'landing-en.html'),
      },
    },
  },
});
