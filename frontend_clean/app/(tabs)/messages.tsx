// Lokasi: app/(app)/(tabs)/messages.tsx

import React from "react";
import { View, Text, SafeAreaView } from "react-native";

export default function MessagesScreen() {
  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-1 justify-center items-center">
        <Text className="text-white text-2xl">Messages Screen</Text>
      </View>
    </SafeAreaView>
  );
}