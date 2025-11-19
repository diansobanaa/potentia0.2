// Lokasi: src/features/dashboard/ui/HomeTopTabs.tsx

import React from "react";
import { View, Text, TouchableOpacity, Dimensions, StyleSheet } from "react-native";
import Animated, {
  useAnimatedStyle,
  interpolate,
  Extrapolation,
} from "react-native-reanimated";

const { width } = Dimensions.get("window");
const TABS = ["For you", "Following"];

interface HomeTopTabsProps {
  scrollX: Animated.SharedValue<number>;
  onTabPress: (index: number) => void;
}

export function HomeTopTabs({ scrollX, onTabPress }: HomeTopTabsProps) {
  // Style animasi untuk indikator (garis biru)
  const indicatorAnimatedStyle = useAnimatedStyle(() => {
    // 0 -> 0, width -> 1
    const inputRange = TABS.map((_, i) => i * width);
    const outputRange = TABS.map((_, i) => (width / TABS.length) * i);

    const translateX = interpolate(
      scrollX.value,
      inputRange,
      outputRange,
      Extrapolation.CLAMP
    );

    return {
      transform: [{ translateX: translateX }],
    };
  });

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        {TABS.map((tab, index) => {
          // Style animasi untuk teks (transisi opacity)
          const textAnimatedStyle = useAnimatedStyle(() => {
            const position = width * index;
            // Jarak dari tab saat ini
            const distance = Math.abs(scrollX.value - position);
            // Opacity: 1 saat di tab, 0.7 saat di tab lain
            const opacity = interpolate(
              distance,
              [0, width],
              [1, 0.7],
              Extrapolation.CLAMP
            );
            return { opacity };
          });

          return (
            <TouchableOpacity
              key={tab}
              onPress={() => onTabPress(index)}
              style={styles.tabButton}
            >
              <Animated.View style={textAnimatedStyle}>
                <Text style={styles.tabText}>{tab}</Text>
              </Animated.View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Indikator Slider Biru */}
      <Animated.View
        style={[indicatorAnimatedStyle, styles.indicator, { width: width / TABS.length }]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#000",
    borderBottomWidth: 1,
    borderBottomColor: "#262626",
  },
  row: { flexDirection: "row" },
  tabButton: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
  },
  tabText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  indicator: { height: 4, backgroundColor: "#3b82f6", borderRadius: 9999 },
});