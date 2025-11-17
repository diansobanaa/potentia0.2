// Lokasi: app/(app)/_layout.tsx

import React from "react";
import { Platform } from "react-native";
import { Drawer } from "expo-router/drawer";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { CustomDrawerContent } from "@/src/features/dashboard/ui/CustomDrawerContent";

export default function AppLayout({ children }: { children?: React.ReactNode }) {
  // Persistent sidebar for web, Drawer for mobile
  if (Platform.OS === 'web') {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', background: '#111' }}>
        <aside style={{ width: 350, background: '#18181b', borderRight: '1px solid #222', overflowY: 'auto' }}>
          <CustomDrawerContent />
        </aside>
        <main style={{ flex: 1, background: '#111', overflowY: 'auto' }}>
          {children}
        </main>
      </div>
    );
  }
  // Mobile/tablet: Drawer
  const drawerWidth = '80%';
  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: "black" }}>
      <Drawer
        drawerContent={CustomDrawerContent}
        screenOptions={{
          headerShown: false,
          drawerType: "slide",
          overlayColor: "rgba(0, 0, 0, 0.5)",
          swipeEnabled: true,
          swipeEdgeWidth: 50,
          drawerStyle: {
            backgroundColor: "black",
            width: drawerWidth,
          },
        }}
      >
        <Drawer.Screen name="(tabs)" options={{ headerShown: false }} />
      </Drawer>
    </GestureHandlerRootView>
  );
}
