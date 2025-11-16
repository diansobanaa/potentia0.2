// Lokasi: src/shared/config/env.ts

// Pastikan Anda telah membuat file .env di root folder 'frontend/'
// dan mengisinya berdasarkan .env.example

const API_URL = process.env.EXPO_PUBLIC_API_URL;
const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

if (!API_URL || !SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error("Kesalahan: Variabel lingkungan (env) belum diatur.");
  throw new Error(
    "Variabel lingkungan (EXPO_PUBLIC_...) belum di-set di file .env"
  );
}

export const env = {
  API_URL,
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
};