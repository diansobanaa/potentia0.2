// Lokasi: src/features/dashboard/ui/CustomDrawerContent.tsx

import React from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from "react-native";
import { Link, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { supabase } from "@/src/shared/api/supabase";
import { useAuthActions, useAuthUser } from "@/src/features/auth/store";
import { Avatar } from "@/src/entities/user/ui/Avatar";

// Komponen link untuk item menu
const DrawerLink = ({ href, text }: { href: string; text: string }) => (
  <Link href={href} asChild>
    <TouchableOpacity style={styles.linkItem}>
      <Text style={styles.linkText}>{text}</Text>
    </TouchableOpacity>
  </Link>
);

export function CustomDrawerContent() {
  const router = useRouter();
  const insets = useSafeAreaInsets(); // Untuk padding atas (area notch)
  const user = useAuthUser();
  const { logout } = useAuthActions();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    logout();
    router.replace("/(auth)/login");
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* --- Header Profil --- */}
        <Link href="/(app)/profile" asChild>
          <TouchableOpacity style={styles.profileHeader}>
            <Avatar source={null} name={user?.name || user?.email} size="medium" />
            <Text style={styles.profileName}>{user?.name || "Anonymous"}</Text>
            <Text style={styles.profileHandle}>@{user?.email?.split("@")[0] || "user"}</Text>
            <View style={styles.followRow}>
              <Text style={styles.followText}><Text style={styles.followBold}>135</Text> Following</Text>
              <Text style={styles.followText}><Text style={styles.followBold}>86</Text> Followers</Text>
            </View>
          </TouchableOpacity>
        </Link>

        {/* --- Daftar Link Navigasi --- */}
        <View style={styles.linksGroup}>
          <DrawerLink href="/(app)/profile" text="Profile" />
          <DrawerLink href="/(app)/premium" text="Premium" />
          <DrawerLink href="/(app)/bookmarks" text="Bookmarks" />
          <DrawerLink href="/(app)/lists" text="Lists" />
          <DrawerLink href="/(app)/spaces" text="Spaces" />
          <DrawerLink href="/(app)/monetization" text="Monetization" />
        </View>

        {/* --- Divider --- */}
        <View style={styles.divider} />

        <View style={styles.linksGroup}>
          <DrawerLink href="/(app)/settings" text="Settings and privacy" />
          <DrawerLink href="/(app)/help" text="Help Center" />
        </View>
      </ScrollView>

      {/* --- Tombol Logout di Bawah --- */}
      <View style={styles.logoutBar}>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
          <Text style={styles.logoutText}>Log out</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  scrollContent: { padding: 24 },
  profileHeader: { marginBottom: 16 },
  profileName: { color: "#fff", fontSize: 24, fontWeight: "700", marginTop: 8 },
  profileHandle: { color: "#a3a3a3", fontSize: 16 },
  followRow: { flexDirection: "row", gap: 16, marginTop: 12 },
  followText: { color: "#fff" },
  followBold: { fontWeight: "700" },
  linksGroup: { gap: 8 },
  divider: { height: 1, backgroundColor: "#262626", marginVertical: 16 },
  linkItem: { paddingVertical: 12 },
  linkText: { color: "#fff", fontSize: 20, fontWeight: "700" },
  logoutBar: { padding: 24, borderTopWidth: 1, borderTopColor: "#262626" },
  logoutButton: { paddingVertical: 8 },
  logoutText: { color: "#fff", fontSize: 18, fontWeight: "700" },
});