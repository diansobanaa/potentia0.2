// app/(mobile)/_layout.tsx
import React, { useState, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Dimensions,
  Animated,
  PanResponder,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Tabs, usePathname, useRouter } from "expo-router";
import { CustomDrawerContent } from "@/src/features/dashboard/ui/CustomDrawerContent";
import { TabBarIcon } from "@/src/shared/ui/TabBarIcon";

const { width } = Dimensions.get("window");
const SIDEBAR_WIDTH = width * 0.78;

export default function MobileLayout() {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const slideAnim = useRef(new Animated.Value(-SIDEBAR_WIDTH)).current;

  const openSidebar = () => {
    setSidebarOpen(true);
    Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true }).start();
  };

  const closeSidebar = () => {
    Animated.spring(slideAnim, { toValue: -SIDEBAR_WIDTH, useNativeDriver: true }).start(() => {
      setSidebarOpen(false);
    });
  };

  const panResponder = PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 10,
    onPanResponderMove: (_, g) => {
      if (sidebarOpen) slideAnim.setValue(g.dx);
      else if (g.dx > 0) slideAnim.setValue(-SIDEBAR_WIDTH + g.dx);
    },
    onPanResponderRelease: (_, g) => {
      if (g.dx > 80 || g.vx > 0.5) openSidebar();
      else if (g.dx < -80 || g.vx < -0.5) closeSidebar();
      else Animated.spring(slideAnim, { toValue: sidebarOpen ? 0 : -SIDEBAR_WIDTH, useNativeDriver: true }).start();
    },
  });

  const overlayOpacity = slideAnim.interpolate({
    inputRange: [-SIDEBAR_WIDTH, 0],
    outputRange: [0, 0.5],
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#000" }}>
      <View style={{ flex: 1 }} {...panResponder.panHandlers}>
        {/* Overlay */}
        <Animated.View
          style={[StyleSheet.absoluteFillObject, { backgroundColor: "#000", opacity: overlayOpacity, zIndex: 10 }]}
          pointerEvents={sidebarOpen ? "auto" : "none"}
        >
          <TouchableOpacity style={{ flex: 1 }} onPress={closeSidebar} />
        </Animated.View>

        {/* Sidebar */}
        <Animated.View style={[styles.sidebar, { transform: [{ translateX: slideAnim }] }]}>
          <CustomDrawerContent sidebarWidth={SIDEBAR_WIDTH} />
        </Animated.View>

        {/* Main Content */}
        <View style={{ flex: 1 }}>
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity onPress={openSidebar} hitSlop={20}>
              <Ionicons name="menu" size={28} color="white" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>X</Text>
            <Ionicons name="logo-twitter" size={28} color="#1d9bf0" />
          </View>

          {/* Tabs */}
          <Tabs
            screenOptions={{
              headerShown: false,
              tabBarStyle: {
                backgroundColor: "#000",
                borderTopWidth: 0,
                height: 60,
                paddingBottom: 0,
              },
              tabBarShowLabel: false,
              tabBarActiveTintColor: "#1d9bf0",
              tabBarInactiveTintColor: "#8899a6",
            }}
          >
            <Tabs.Screen
              name="home"
              options={{
                tabBarIcon: ({ color, focused }) => (
                  <Ionicons name={focused ? "home" : "home-outline"} size={28} color={color} />
                ),
              }}
            />
            <Tabs.Screen
              name="search"
              options={{
                tabBarIcon: ({ color, focused }) => (
                  <Ionicons name={focused ? "search" : "search-outline"} size={28} color={color} />
                ),
              }}
            />
            <Tabs.Screen
              name="notifications"
              options={{
                tabBarIcon: ({ color, focused }) => (
                  <Ionicons name={focused ? "heart" : "heart-outline"} size={28} color={color} />
                ),
              }}
            />
            <Tabs.Screen
              name="messages"
              options={{
                tabBarIcon: ({ color, focused }) => (
                  <Ionicons name={focused ? "mail" : "mail-outline"} size={28} color={color} />
                ),
              }}
            />
            <Tabs.Screen
              name="chat"
              options={{
                // Kunci untuk menyembunyikan tab ini dari UI tab bar:
                // Mengatur href ke null memberitahu Expo Router untuk tidak merender tab ini.
                href: null, 
                
                // Properti ini tetap bisa dipertahankan, meskipun tidak akan pernah dirender
                tabBarIcon: ({ color, focused }) => (
                  <Ionicons name={focused ? "mail" : "mail-outline"} size={28} color={color} />
                ),
                
                // Contoh: Nama tab juga dihilangkan
                title: "", 
                
                // Opsi lainnya (misalnya, untuk menyembunyikan header)
                headerShown: false, 
              }}
            />
          </Tabs>
            
          {/* FAB hanya tampil jika bukan di halaman chat */}
          {!(pathname && pathname.includes('/chat')) && (
            <TouchableOpacity style={styles.fab}>
              <Ionicons name="sparkles" size={32} color="#fcfcfcff" />
            </TouchableOpacity>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  sidebar: {
    position: "absolute",
    left: 0,
    top: 0,
    width: SIDEBAR_WIDTH,
    height: "100%",
    backgroundColor: "#000",
    zIndex: 20,
    borderRightWidth: 1,
    borderRightColor: "#2f3336",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    height: 56,
    backgroundColor: "#000",
    borderBottomWidth: 1,
    borderBottomColor: "#2f3336",
  },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "bold" },
  fab: {
    position: "absolute",
    right: 16,
    bottom: 150,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#1d9bf0",
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 10,
  },
});