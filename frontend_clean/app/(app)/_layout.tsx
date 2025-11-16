// Lokasi: app/(app)/_layout.tsx

import React from "react";
import { View } from "react-native";
import { Drawer } from "expo-router/drawer";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { CustomDrawerContent } from "@/src/features/dashboard/ui/CustomDrawerContent";
// Catatan: Animasi konten (scale/translate/borderRadius) dipindahkan
// ke `app/(tabs)/_layout.tsx` agar sesuai aturan expo-router.

export default function AppLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: "black" }}>
      <Drawer
        // Tunjuk ke komponen UI kustom kita (Fase 4)
        drawerContent={CustomDrawerContent}
        screenOptions={{
          headerShown: false, // Sembunyikan header default
          drawerType: "slide", // Tipe "slide" untuk efek "X-style"
          overlayColor: "transparent", // Tidak ada bayangan
          drawerStyle: {
            backgroundColor: "black",
            width: "80%", // Lebar sidebar
          },
          sceneContainerStyle: {
            backgroundColor: "black", // Latar belakang di belakang scene
          },
        }}
      >
        {/* Deklarasikan screen tanpa children sesuai aturan layout routes */}
        <Drawer.Screen name="(tabs)" options={{ headerShown: false }} />
        {/* Tambahkan layar lain yang bisa diakses dari Drawer di sini */}
        {/* Contoh: <Drawer.Screen name="profile" /> */}
      </Drawer>
    </GestureHandlerRootView>
  );
}