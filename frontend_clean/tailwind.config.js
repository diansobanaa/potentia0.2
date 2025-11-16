// Lokasi: frontend/tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Arahkan NativeWind untuk men-scan semua file .tsx
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  
  // Use NativeWind preset for React Native styling compatibility
  presets: [require("nativewind/preset")],
  
  // Use class-based dark mode
  darkMode: 'class',
  
  theme: {
    extend: {
      colors: {
        // (Warna kustom kita)
        'potentia-primary': '#FFFFFF',
        'potentia-dark': '#0A0A0A',
        'potentia-blue': '#1D9BF0',
        'potentia-grey-light': '#71717a',
        'potentia-grey-dark': '#27272a',
      }
    },
  },
  plugins: [],
};