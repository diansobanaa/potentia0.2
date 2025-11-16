// Relocated: app/(app)/(tabs)/home/foryou.tsx
import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";

export default function ForYouScreen() {
  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>For You Feed</Text>
        <Text style={styles.subtitle}>Konten rekomendasi akan muncul di sini</Text>
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
