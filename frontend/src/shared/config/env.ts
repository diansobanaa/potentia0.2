// Lokasi: src/shared/config/env.ts

import { Platform } from "react-native";

// Catatan: di Expo Web, nilai `process.env.EXPO_PUBLIC_...` akan di-replace saat build.
// Hindari throw pada import agar UI tidak blank ketika env belum lengkap.

const RAW_API_URL = process.env.EXPO_PUBLIC_API_URL || "";
// Opsional: gunakan URL LAN untuk perangkat native (hindari localhost di iOS/Android)
const RAW_API_URL_LAN = process.env.EXPO_PUBLIC_API_URL_LAN || "";
const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || "";

// Tentukan API_URL efektif berdasarkan platform
// - Web: gunakan RAW_API_URL langsung
// - Native: jika RAW_API_URL mengandung "localhost"/"127.0.0.1"/"0.0.0.0" dan tersedia RAW_API_URL_LAN, gunakan itu
let API_URL = RAW_API_URL;
if (Platform.OS !== "web") {
  const isLocalhost =
    /(^|\/)localhost(?::\d+)?\/?/i.test(RAW_API_URL) ||
    RAW_API_URL.includes("127.0.0.1") ||
    RAW_API_URL.includes("0.0.0.0");
  if (isLocalhost && RAW_API_URL_LAN) {
    API_URL = RAW_API_URL_LAN;
  }
}

// Peringatan ramah jika env belum lengkap (tanpa menghentikan app)
const missing: string[] = [];
if (!API_URL) missing.push("EXPO_PUBLIC_API_URL");
if (!SUPABASE_URL) missing.push("EXPO_PUBLIC_SUPABASE_URL");
if (!SUPABASE_ANON_KEY) missing.push("EXPO_PUBLIC_SUPABASE_ANON_KEY");
if (missing.length) {
  // eslint-disable-next-line no-console
  console.warn(
    `[env] Missing env vars: ${missing.join(", ")}. UI tetap jalan, tapi fitur tertentu mungkin tidak berfungsi. ` +
      `Set juga EXPO_PUBLIC_API_URL_LAN untuk perangkat iOS/Android bila backend tidak di localhost.`
  );
}

export const env = {
  API_URL,
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
};