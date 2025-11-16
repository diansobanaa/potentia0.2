// Lokasi: src/features/dashboard/ui/HomeHeader.tsx

import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useNavigation } from "expo-router";
import { DrawerActions } from "@react-navigation/drawer";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Avatar } from "@/src/entities/user/ui/Avatar";
import { useAuthUser } from "@/src/features/auth/store";

export function HomeHeader() {
  const navigation = useNavigation();
  const user = useAuthUser();
  const insets = useSafeAreaInsets();

  const openDrawer = () => {
    try {
      // Try to find the drawer navigator in the parent chain
      let currentNav: any = navigation;
      while (currentNav) {
        const state = currentNav.getState?.();
        if (state?.type === 'drawer') {
          currentNav.dispatch(DrawerActions.openDrawer());
          return;
        }
        currentNav = currentNav.getParent?.();
      }
      // Fallback
      navigation.dispatch(DrawerActions.openDrawer());
    } catch (error) {
      console.error('Failed to open drawer:', error);
    }
  };

  return (
    <View style={[styles.headerContainer, { paddingTop: insets.top }]}>
      <View style={styles.headerRow}>
        {/* Kiri: Tombol Avatar untuk buka Drawer */}
        <TouchableOpacity onPress={openDrawer}>
          <Avatar source={null} name={user?.name || user?.email} size="small" />
        </TouchableOpacity>

        {/* Tengah: Logo "X" */}
        <View>
          <Text style={styles.logo}>X</Text>
        </View>

        {/* Kanan: Spacer (agar logo tetap di tengah) */}
        <View style={{ width: 40 }} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  headerContainer: {
    backgroundColor: "rgba(0,0,0,0.8)",
    borderBottomWidth: 1,
    borderBottomColor: "#262626",
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    height: 56,
    paddingHorizontal: 16,
  },
  logo: { color: "#fff", fontSize: 30, fontWeight: "800" },
});