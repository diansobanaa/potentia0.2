// Lokasi: app/(app)/(tabs)/home/following.tsx

import React from "react";
import { View, Text } from "react-native";

export default function FollowingScreen() {
  return (
    <View className="flex-1 bg-black justify-center items-center">
      <Text className="text-white text-xl">Following Feed</Text>
      <Text className="text-neutral-500 mt-2">
        Konten akan muncul di sini
      </Text>
    </View>
  );
}