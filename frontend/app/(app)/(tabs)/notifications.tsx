// Relocated: app/(app)/(tabs)/notifications.tsx
import React from "react";
import { View, Text, SafeAreaView, StyleSheet } from "react-native";

export default function NotificationsScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.center}>
        <Text style={styles.title}>Notifications Screen</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: { color: "#fff", fontSize: 24, fontWeight: "600" },
});
