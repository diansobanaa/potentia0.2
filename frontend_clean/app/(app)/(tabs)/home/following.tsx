// Relocated: app/(app)/(tabs)/home/following.tsx
import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";

export default function FollowingScreen() {
  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Following Feed</Text>
        <Text style={styles.subtitle}>Konten akan muncul di sini</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  title: { color: "#fff", fontSize: 20, fontWeight: "600" },
  subtitle: { color: "#a3a3a3", marginTop: 8 },
});
