// app/(mobile)/home/foryou.tsx
import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";

export default function ForYouScreen() {
  return (
    <ScrollView style={styles.container}>
      <View style={styles.tweet}>
        <Text style={styles.username}>@elonmusk</Text>
        <Text style={styles.content}>Just setting up my X</Text>
      </View>
      {/* Tambahin tweet lain di sini */}
      <Text style={styles.placeholder}>Ini halaman For You</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  tweet: { padding: 16, borderBottomWidth: 1, borderColor: "#2f3336" },
  username: { color: "#1d9bf0", fontWeight: "bold" },
  content: { color: "white", marginTop: 4, fontSize: 16 },
  placeholder: { color: "white", textAlign: "center", marginTop: 100, fontSize: 18 },
});