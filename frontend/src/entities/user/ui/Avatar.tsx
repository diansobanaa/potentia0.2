// Lokasi: src/entities/user/ui/Avatar.tsx


import React from "react";
import { Image, View, Text, StyleSheet } from "react-native";

interface AvatarProps {
  source?: string | null;
  name?: string | null;
  size?: "small" | "medium";
}

export const Avatar = React.forwardRef<View, AvatarProps>(
  function Avatar({ source, name, size = "medium" }, ref) {
    const sizeStyle = size === "medium" ? styles.sizeMd : styles.sizeSm;
    const textStyle = size === "medium" ? styles.textMd : styles.textSm;

    // Ambil inisial jika tidak ada gambar
    const initials =
      name
        ?.split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase() || "?";

    return (
      <View ref={ref} style={[styles.container, sizeStyle]}>
        {source ? (
          <Image source={{ uri: source }} style={styles.image} />
        ) : (
          <Text style={[textStyle, styles.text]}>{initials}</Text>
        )}
      </View>
    );
  }
);

const styles = StyleSheet.create({
  container: {
    borderRadius: 9999,
    backgroundColor: "#404040",
    justifyContent: "center",
    alignItems: "center",
    overflow: "hidden",
  },
  sizeMd: { width: 48, height: 48 },
  sizeSm: { width: 40, height: 40 },
  image: { width: "100%", height: "100%" },
  text: { color: "#fff", fontWeight: "700" },
  textMd: { fontSize: 20 },
  textSm: { fontSize: 18 },
});