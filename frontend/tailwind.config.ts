import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#1e1e2e',
        panel: '#181825',
        surface: '#232334',
        border: '#313244',
        accent: '#89b4fa',
        muted: '#6c7086',
      },
    },
  },
  plugins: [],
} satisfies Config
