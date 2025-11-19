// Relocated: app/(app)/(tabs)/search.tsx
import React from "react";
import { SafeAreaView, View, Text, StyleSheet } from "react-native";

export default function SearchScreen() {
  return (
    <SafeAreaView style={styles.container}>
      
      <View style={styles.center}>
        <Text style={styles.title}>Search</Text>
        <Text style={styles.subtitle}>Feature coming soon</Text>
        
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: { color: "#fff", fontSize: 24, fontWeight: "600" },
  subtitle: { color: "#a3a3a3", marginTop: 8 },
});
