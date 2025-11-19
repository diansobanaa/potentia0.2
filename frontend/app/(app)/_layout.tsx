import React from "react";
import { View } from "react-native";
import { Slot } from "expo-router";

export default function AppLayout() {
  // Gunakan <Slot /> untuk merender screen/halaman yang sedang aktif.
  // Bungkus dengan View flex: 1 agar konten mengambil tinggi penuh layar.
  return (
    <View style={{ flex: 1 }}>
      <Slot />
    </View>
  );
}