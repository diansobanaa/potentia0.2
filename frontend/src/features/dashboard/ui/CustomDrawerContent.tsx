// Lokasi: src/features/dashboard/ui/CustomDrawerContent.tsx

import React from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Link, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { supabase } from "@/src/shared/api/supabase";
import { useAuthActions, useAuthUser } from "@/src/features/auth/store";
import { Avatar } from "@/src/entities/user/ui/Avatar";
import ListConversationSidebar from "@/src/features/chat/ui/ListConversationSidebar";

// Komponen menu item dengan icon
const MenuItem = ({ icon, text, onPress }: { icon: string; text: string; onPress?: () => void }) => (
  <TouchableOpacity style={styles.menuItem} onPress={onPress} activeOpacity={0.7}>
    <Ionicons name={icon as any} size={24} color="#fff" style={styles.menuIcon} />
    <Text style={styles.menuText}>{text}</Text>
  </TouchableOpacity>
);

export function CustomDrawerContent() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const user = useAuthUser();
  const { logout } = useAuthActions();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    logout();
    router.replace("/(auth)/login");
  };

  // Fungsi penutup drawer/sidebar (ganti sesuai implementasi parent)
  const handleCloseSidebar = () => {
    // TODO: Ganti dengan fungsi penutup drawer/modal yang sesuai
    // Contoh: jika pakai context/modal, panggil setShowDrawer(false) atau navigation.closeDrawer()
    if (router.canGoBack && router.back) {
      router.back();
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}> 
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Header Profile */}
        <View style={styles.profileSection}>
          <Avatar source={null} name={user?.name || user?.email} size="medium" />
          <Text style={styles.profileName}>{user?.name || "Dian Sobana"}</Text>
          <Text style={styles.profileHandle}>@{user?.email?.split("@")[0] || "DsobBonek"}</Text>
          
          <View style={styles.statsRow}>
            <Text style={styles.statsText}>
              <Text style={styles.statsBold}>135</Text>
              <Text style={styles.statsLabel}> Following</Text>
            </Text>
            <Text style={styles.statsText}>
              <Text style={styles.statsBold}>86</Text>
              <Text style={styles.statsLabel}> Followers</Text>
            </Text>
          </View>
        </View>

        {/* Menu Items */}
        <View style={styles.menuSection}>
          <MenuItem icon="person-outline" text="Profile" onPress={() => router.push("/(app)/profile" as any)} />
          <MenuItem icon="logo-twitter" text="Premium" onPress={() => router.push("/(app)/premium" as any)} />
          <MenuItem icon="play-circle-outline" text="Video" onPress={() => {}} />
          <MenuItem icon="chatbubble-outline" text="Chat" onPress={() => {}} />
          <ListConversationSidebar onPress={handleCloseSidebar} />
          <MenuItem icon="people-outline" text="Communities" onPress={() => {}} />
          <MenuItem icon="bookmark-outline" text="Bookmarks" onPress={() => router.push("/(app)/bookmarks" as any)} />
          <MenuItem icon="list-outline" text="Lists" onPress={() => router.push("/(app)/lists" as any)} />
          <MenuItem icon="mic-outline" text="Spaces" onPress={() => router.push("/(app)/spaces" as any)} />
          <MenuItem icon="cash-outline" text="Monetization" onPress={() => router.push("/(app)/monetization" as any)} />
        </View>

        {/* Divider */}
        <View style={styles.divider} />

        {/* Bottom Menu Items */}
        <View style={styles.menuSection}>
          <MenuItem icon="leaf-outline" text="Open Grok" onPress={() => {}} />
          <MenuItem icon="settings-outline" text="Settings and privacy" onPress={() => router.push("/(app)/settings" as any)} />
          <MenuItem icon="log-out-outline" text="Log out" onPress={handleLogout} />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  scrollContent: { paddingLeft: 16 },
  profileSection: { 
    marginBottom: 24,
    paddingBottom: 12
  },
  profileName: { 
    color: "#fff", 
    fontSize: 20, 
    fontWeight: "700", 
    marginTop: 12,
    marginBottom: 4
  },
  profileHandle: { 
    color: "#71767b", 
    fontSize: 15,
    marginBottom: 12
  },
  statsRow: { 
    flexDirection: "row", 
    gap: 20 
  },
  statsText: { 
    color: "#71767b",
    fontSize: 15
  },
  statsBold: { 
    color: "#fff",
    fontWeight: "700" 
  },
  statsLabel: {
    color: "#71767b"
  },
  menuSection: { 
    gap: 4,
    marginBottom: 8
  },
  menuItem: { 
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 16,
    gap: 20
  },
  menuIcon: {
    width: 24,
    height: 24
  },
  menuText: { 
    color: "#fff", 
    fontSize: 20,
    fontWeight: "400"
  },
  divider: { 
    height: 1, 
    backgroundColor: "#2f3336", 
    marginVertical: 12 
  }
});