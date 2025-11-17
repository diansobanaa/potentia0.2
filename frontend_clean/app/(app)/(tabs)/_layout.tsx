// Relocated: app/(app)/(tabs)/_layout.tsx

import React, { useEffect } from "react";
import { Tabs, useRouter, usePathname } from "expo-router";
import { TabBarIcon } from "@/src/shared/ui/TabBarIcon";
import { HomeHeader } from "@/src/features/dashboard/ui/HomeHeader";
import { useDrawerProgress } from "@react-navigation/drawer";
import Animated, { interpolate, useAnimatedStyle } from "react-native-reanimated";
import { Dimensions } from "react-native";

const { width } = Dimensions.get("window");

export default function TabsLayout({ children }: { children?: React.ReactNode }) {
  const progress = useDrawerProgress();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Redirect /home or / to /chat as default tab
    if (pathname === "/home" || pathname === "/") {
      router.replace("/chat");
    }
  }, [pathname, router]);

  const animatedStyle = useAnimatedStyle(() => {
    const scale = interpolate(progress.value, [0, 1], [1, 0.8]);
    const translateX = interpolate(progress.value, [0, 1], [0, width * 0.65]);
    const borderRadius = interpolate(progress.value, [0, 1], [0, 30]);
    return { borderRadius, transform: [{ scale }, { translateX }] };
  });

  return (
    <Animated.View style={[{ flex: 1, overflow: "hidden" }, animatedStyle]}>
      <Tabs
        screenOptions={{
          headerShown: true,
          header: () => <HomeHeader />,
          tabBarShowLabel: false,
          tabBarActiveTintColor: "white",
          tabBarInactiveTintColor: "gray",
          tabBarStyle: { backgroundColor: "black", borderTopWidth: 0 },
        }}
      >
        <Tabs.Screen
          name="home"
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
          name="chat"
          options={{
            title: "Chat",
            href: "/chat",
            tabBarIcon: ({ color, focused }) => (
              <TabBarIcon name="chatbubbles" color={color} focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="chat/[conversation_id]"
          options={{
            href: null,
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
      {children}
    </Animated.View>
  );
}
