// Lokasi: app/(app)/(tabs)/home.tsx
// (Nama file diubah dari index.tsx ke home.tsx)

import { Redirect } from "expo-router";

// File ini adalah 'entry point' untuk tab 'home'.
// Kita langsung arahkan (redirect) ke 'foryou' yang akan jadi default.
// Ini akan memuat layout di app/(app)/(tabs)/home/
export default function HomeTab() {
  return <Redirect href="/(app)/(tabs)/home/foryou" />;
}