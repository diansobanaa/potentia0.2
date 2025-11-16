// Lokasi: app/(tabs)/home/foryou.tsx

import React from "react";
import { View, Text } from "react-native";

export default function ForYouScreen() {
  return (
    <View className="flex-1 bg-black justify-center items-center">
      <Text className="text-white text-xl">For You Feed</Text>
      <Text className="text-neutral-500 mt-2">
        Konten rekomendasi akan muncul di sini
      </Text>
    </View>
  );
}
