import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/matchups': 'https://pickem.lbrt.net',
      '/picks': 'https://pickem.lbrt.net',
      '/me': 'https://pickem.lbrt.net',
      '/stats': 'https://pickem.lbrt.net',
      '/scores': 'https://pickem.lbrt.net',
      '/stat-guide': 'https://pickem.lbrt.net',
      '/rosters': 'https://pickem.lbrt.net',
      '/admin': 'https://pickem.lbrt.net',
      '/auth': 'https://pickem.lbrt.net',
    },
  },
})
