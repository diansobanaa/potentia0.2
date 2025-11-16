// Lokasi: src/features/dashboard/ui/HomeHeader.tsx

import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { useNavigation } from "expo-router";
import { DrawerActions } from "@react-navigation/drawer";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Avatar } from "@/src/entities/user/ui/Avatar";
import { useAuthUser } from "@/src/features/auth/store";

export function HomeHeader() {
  const navigation = useNavigation();
  const user = useAuthUser();
  const insets = useSafeAreaInsets(); // Untuk padding 'top'

  const openDrawer = () => {
    navigation.dispatch(DrawerActions.openDrawer());
  };

  return (
    <View
      className="bg-black/80 border-b border-neutral-800"
      style={{ paddingTop: insets.top }}
    >
      <View className="flex-row items-center justify-between h-14 px-4">
        {/* Kiri: Tombol Avatar untuk buka Drawer */}
        <TouchableOpacity onPress={openDrawer} className="active:opacity-70">
          <Avatar source={null} name={user?.name || user?.email} size="small" />
        </TouchableOpacity>

        {/* Tengah: Logo "X" */}
        <View>
          <Text className="text-white text-3xl font-extrabold">
            X
          </Text>
        </View>

        {/* Kanan: Spacer (agar logo tetap di tengah) */}
        <View className="w-10" />
      </View>
    </View>
  );
}