// Lokasi: src/features/dashboard/ui/CustomDrawerContent.tsx

import React from "react";
import { View, Text, ScrollView, TouchableOpacity } from "react-native";
import { Link, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { supabase } from "@/src/shared/api/supabase";
import { useAuthActions, useAuthUser } from "@/src/features/auth/store";
import { Avatar } from "@/src/entities/user/ui/Avatar";

// Komponen link untuk item menu
const DrawerLink = ({ href, text }: { href: string; text: string }) => (
  <Link href={href} asChild>
    <TouchableOpacity className="py-3 active:bg-neutral-800">
      <Text className="text-white text-xl font-bold">{text}</Text>
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
    <View
      className="flex-1 bg-black"
      style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}
    >
      <ScrollView className="p-6">
        {/* --- Header Profil --- */}
        <Link href="/(app)/profile" asChild>
          <TouchableOpacity className="mb-4 active:opacity-70">
            <Avatar source={null} name={user?.name || user?.email} size="medium" />
            <Text className="text-white text-2xl font-bold mt-2">
              {user?.name || "Anonymous"}
            </Text>
            <Text className="text-neutral-500 text-base">
              @{user?.email?.split("@")[0] || "user"}
            </Text>
            <View className="flex-row space-x-4 mt-3">
              <Text className="text-white">
                <Text className="font-bold">135</Text> Following
              </Text>
              <Text className="text-white">
                <Text className="font-bold">86</Text> Followers
              </Text>
            </View>
          </TouchableOpacity>
        </Link>

        {/* --- Daftar Link Navigasi --- */}
        <View className="space-y-2">
          <DrawerLink href="/(app)/profile" text="Profile" />
          <DrawerLink href="/(app)/premium" text="Premium" />
          <DrawerLink href="/(app)/bookmarks" text="Bookmarks" />
          <DrawerLink href="/(app)/lists" text="Lists" />
          <DrawerLink href="/(app)/spaces" text="Spaces" />
          <DrawerLink href="/(app)/monetization" text="Monetization" />
        </View>

        {/* --- Divider --- */}
        <View className="h-px bg-neutral-800 my-4" />

        <View className="space-y-2">
          <DrawerLink href="/(app)/settings" text="Settings and privacy" />
          <DrawerLink href="/(app)/help" text="Help Center" />
        </View>
      </ScrollView>

      {/* --- Tombol Logout di Bawah --- */}
      <View className="p-6 border-t border-neutral-800">
        <TouchableOpacity onPress={handleLogout} className="py-2">
          <Text className="text-white text-lg font-bold">
            Log out
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}