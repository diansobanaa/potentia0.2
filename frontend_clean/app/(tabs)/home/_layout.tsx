// Lokasi: app/(app)/(tabs)/home/_layout.tsx

import React, { useRef } from "react";
import { View, Dimensions, FlatList } from "react-native";
import Animated, {
  useAnimatedScrollHandler,
  useSharedValue,
} from "react-native-reanimated";
import { Stack } from "expo-router"; // Gunakan Stack untuk header kustom

import { HomeHeader } from "@/src/features/dashboard/ui/HomeHeader";
import { HomeTopTabs } from "@/src/features/dashboard/ui/HomeTopTabs";
import ForYouScreen from "./foryou"; // Impor layar
import FollowingScreen from "./following"; // Impor layar (kita buat di langkah 5)

const AnimatedFlatList = Animated.createAnimatedComponent(FlatList);

const TABS = [{ key: "foryou" }, { key: "following" }];
const { width } = Dimensions.get("window");

export default function HomeLayout() {
  const scrollX = useSharedValue(0);
  const flatListRef = useRef<FlatList>(null);

  // Handler saat scroll di Pager
  const scrollHandler = useAnimatedScrollHandler((event) => {
    scrollX.value = event.contentOffset.x;
  });

  // Handler saat tombol tab ditekan
  const handleTabPress = (index: number) => {
    flatListRef.current?.scrollToIndex({ index, animated: true });
  };

  return (
    <View className="flex-1 bg-black">
      {/* Kita gunakan <Stack.Screen> dari Expo Router 
        untuk mengontrol header
      */}
      <Stack.Screen
        options={{
          header: () => <HomeHeader />, // Gunakan komponen header kustom kita
        }}
      />

      {/* Komponen Tombol Top Tabs */}
      <HomeTopTabs scrollX={scrollX} onTabPress={handleTabPress} />

      {/* Pager FlatList (Solusi Anda) */}
      <AnimatedFlatList
        ref={flatListRef}
        data={TABS}
        keyExtractor={(item) => item.key}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={scrollHandler}
        scrollEventThrottle={16}
        renderItem={({ item }) => (
          <View style={{ width: width, height: "100%" }}>
            {item.key === "foryou" ? <ForYouScreen /> : <FollowingScreen />}
          </View>
        )}
      />
    </View>
  );
}