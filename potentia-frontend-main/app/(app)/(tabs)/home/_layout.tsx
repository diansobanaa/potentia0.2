// app/(mobile)/home/_layout.tsx
import React from "react";
import { Tabs } from "expo-router";
import { View, Text, StyleSheet, Dimensions, TouchableOpacity } from "react-native";

const { width } = Dimensions.get("window");

export default function HomeLayout() {
  return (
    <Tabs
      tabBar={(props) => <CustomHomeTabBar {...props} />}
      screenOptions={{
        headerShown: false,
        tabBarStyle: { display: "none" },
      }}
    >
      <Tabs.Screen name="foryou" />
      <Tabs.Screen name="following" />
    </Tabs>
  );
}

function CustomHomeTabBar({ state, navigation }: any) {
  const currentIndex = state.index;

  return (
    <View style={styles.container}>
      {/* Header "Home" di atas */}
      <View style={styles.header}>
        <Text style={styles.title}>Home</Text>
      </View>

      {/* Tab For You / Following */}
      <View style={styles.tabContainer}>
        {state.routes.map((route: any, index: number) => {
          const isActive = index === currentIndex;
          const label = route.name === "foryou" ? "For you" : "Following";

          return (
            <TouchableOpacity
              key={route.key}
              style={styles.tab}
              onPress={() => navigation.navigate(route.name)}
              activeOpacity={0.7}
            >
              <Text style={[styles.tabText, isActive && styles.activeText]}>
                {label}
              </Text>
              {isActive && <View style={styles.activeIndicator} />}
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#000",
    borderBottomWidth: 1,
    borderBottomColor: "#2f3336",
  },
  header: {
    height: 56,
    justifyContent: "center",
    alignItems: "center",
  },
  title: {
    color: "white",
    fontSize: 20,
    fontWeight: "bold",
  },
  tabContainer: {
    flexDirection: "row",
    height: 50,
    backgroundColor: "#000",
  },
  tab: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  tabText: {
    color: "#8899a6",
    fontSize: 16,
    fontWeight: "600",
  },
  activeText: {
    color: "white",
  },
  activeIndicator: {
    position: "absolute",
    bottom: 0,
    width: 60,
    height: 3,
    backgroundColor: "#1d9bf0",
    borderRadius: 2,
  },
});