// Lokasi: src/features/dashboard/ui/HomeHeader.tsx

import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, Platform } from "react-native";
import { useNavigation, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Avatar } from "@/src/entities/user/ui/Avatar";
import { useAuthUser } from "@/src/features/auth/store";

export function HomeHeader() {
  const navigation = useNavigation();
  const router = useRouter();
  const user = useAuthUser();
  const insets = useSafeAreaInsets();

  const toggleDrawer = () => {
    console.log('=== Toggle Drawer ===');
    
    try {
      // Try to find the drawer navigator in the parent chain
      let currentNav: any = navigation;
      let depth = 0;
      
      while (currentNav && depth < 10) {
        const state = currentNav.getState?.();
        console.log(`Level ${depth}:`, {
          type: state?.type,
          hasToggle: typeof currentNav.toggleDrawer === 'function',
          hasOpen: typeof currentNav.openDrawer === 'function',
          hasClose: typeof currentNav.closeDrawer === 'function',
          state: state
        });
        
        if (state?.type === 'drawer') {
          console.log('Found drawer at level', depth);
          
          // Prioritize toggleDrawer method for better UX
          if (typeof currentNav.toggleDrawer === 'function') {
            console.log('✓ Calling toggleDrawer');
            currentNav.toggleDrawer();
            return;
          }
          
          // Try dispatch with TOGGLE_DRAWER action
          if (typeof currentNav.dispatch === 'function') {
            console.log('✓ Dispatching TOGGLE_DRAWER');
            currentNav.dispatch({ type: 'TOGGLE_DRAWER' });
            return;
          }
          
          // Fallback to checking state manually
          console.log('No toggle method, trying open/close based on state');
          if (typeof currentNav.closeDrawer === 'function' && typeof currentNav.openDrawer === 'function') {
            // Just toggle without checking state - let the navigation handle it
            console.log('✓ Using closeDrawer (assuming it toggles)');
            currentNav.closeDrawer();
            return;
          }
        }
        currentNav = currentNav.getParent?.();
        depth++;
      }
      
      // Fallback: try direct methods on navigation
      console.log('No drawer in chain, trying direct navigation methods');
      
      if (typeof (navigation as any).toggleDrawer === 'function') {
        console.log('✓ Direct toggleDrawer');
        (navigation as any).toggleDrawer();
        return;
      }
      
      if (typeof navigation.dispatch === 'function') {
        console.log('✓ Direct dispatch toggle');
        navigation.dispatch({ type: 'TOGGLE_DRAWER' } as any);
        return;
      }
      
      console.error('❌ No method found to toggle drawer');
      
    } catch (error) {
      console.error('❌ Failed to toggle drawer:', error);
    }
  };

  return (
    <View style={[styles.headerContainer, { paddingTop: insets.top }]}>
      <View style={styles.headerRow}>
        {/* Kiri: Tombol Avatar untuk toggle Drawer */}
        <TouchableOpacity 
          onPress={toggleDrawer}
          style={styles.avatarButton}
          activeOpacity={0.7}
        >
          <Avatar source={null} name={user?.name || user?.email} size="small" />
        </TouchableOpacity>

        {/* Tengah: Logo "X" */}
          <View>
            <Text style={styles.logo}>Dirga Mahardika</Text>
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
  avatarButton: {
    cursor: Platform.OS === 'web' ? 'pointer' : undefined,
  } as any,
  logo: { color: "#fff", fontSize: 30, fontWeight: "800" },
});