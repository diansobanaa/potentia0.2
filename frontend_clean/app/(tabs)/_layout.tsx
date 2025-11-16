// Lokasi: app/(app)/(tabs)/_layout.tsx

import React from "react";
import { Tabs } from "expo-router";
import { TabBarIcon } from "@/src/shared/ui/TabBarIcon"; // Helper ikon kita
import { useDrawerProgress } from "@react-navigation/drawer";
import Animated, { interpolate, useAnimatedStyle } from "react-native-reanimated";
import { Dimensions } from "react-native";

// Lebar layar untuk animasi gaya "X-style"
const { width } = Dimensions.get("window");

export default function TabsLayout() {
  const progress = useDrawerProgress();

  // Animasi konten utama saat drawer terbuka
  const animatedStyle = useAnimatedStyle(() => {
    const scale = interpolate(progress.value, [0, 1], [1, 0.8]);
    const translateX = interpolate(progress.value, [0, 1], [0, width * 0.65]);
    const borderRadius = interpolate(progress.value, [0, 1], [0, 30]);
    return {
      borderRadius,
      transform: [{ scale }, { translateX }],
    };
  });

  return (
    <Animated.View style={[{ flex: 1, overflow: "hidden" }, animatedStyle]}>
      <Tabs
        screenOptions={{
          headerShown: false, // Header akan kita buat kustom di dalam 'home'
          
          // --- Styling "X-style" ---
          tabBarShowLabel: false, // Sembunyikan label (Hanya ikon)
          tabBarActiveTintColor: "white", // Warna ikon aktif
          tabBarInactiveTintColor: "gray", // Warna ikon tidak aktif
          tabBarStyle: {
            backgroundColor: "black", // Latar belakang tab bar
            borderTopWidth: 0, // Hapus garis border atas
          },
        }}
      >
        <Tabs.Screen
          name="home" // Ini akan menunjuk ke file 'home.tsx'
          options={{
            title: "Home",
            tabBarIcon: ({ color, focused }) => (
              <TabBarIcon name="home" color={color} focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="search"
          options={{
            title: "Search",
            tabBarIcon: ({ color, focused }) => (
              <TabBarIcon name="search" color={color} focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="notifications"
          options={{
            title: "Notifications",
            tabBarIcon: ({ color, focused }) => (
              <TabBarIcon name="notifications" color={color} focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="messages"
          options={{
            title: "Messages",
            tabBarIcon: ({ color, focused }) => (
              <TabBarIcon name="mail" color={color} focused={focused} />
            ),
          }}
        />
      </Tabs>
    </Animated.View>
  );
}