// Vite config to disable CSS source maps and fix style.css.map error
import { defineConfig } from 'vite';

export default defineConfig({
  css: {
    devSourcemap: false,
  },
});
