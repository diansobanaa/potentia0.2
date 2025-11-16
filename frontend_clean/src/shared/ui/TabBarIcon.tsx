// Lokasi: src/shared/ui/TabBarIcon.tsx

import React from "react";
import { Ionicons } from "@expo/vector-icons"; // Menggunakan set ikon Ionicons

interface TabBarIconProps {
  name: React.ComponentProps<typeof Ionicons>["name"];
  color: string;
  focused: boolean;
}

export function TabBarIcon({ name, color, focused }: TabBarIconProps) {
  // Tampilkan ikon 'filled' jika 'focused', dan 'outline' jika tidak
  const iconName = focused ? name : (`${name}-outline` as any);

  return <Ionicons size={26} name={iconName} color={color} />;
}