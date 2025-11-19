// app/(mobile)/home/following.tsx
import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";

export default function FollowingScreen() {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.placeholder}>Ini halaman Following</Text>
      <Text style={styles.info}>Kamu belum follow siapa-siapa</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  placeholder: { color: "white", textAlign: "center", marginTop: 100, fontSize: 18, fontWeight: "bold" },
  info: { color: "#8899a6", textAlign: "center", marginTop: 10 },
});