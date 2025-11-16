// Lokasi: app/(app)/(tabs)/notifications.tsx

import React from "react";
import { View, Text, SafeAreaView } from "react-native";

export default function NotificationsScreen() {
  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-1 justify-center items-center">
        <Text className="text-white text-2xl">
          Notifications Screen
        </Text>
      </View>
    </SafeAreaView>
  );
}