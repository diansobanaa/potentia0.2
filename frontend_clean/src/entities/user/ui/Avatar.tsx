// Lokasi: src/entities/user/ui/Avatar.tsx

import { Image, View, Text } from "react-native";

interface AvatarProps {
  source?: string | null;
  name?: string | null;
  size?: "small" | "medium";
}

export function Avatar({ source, name, size = "medium" }: AvatarProps) {
  const sizeClasses =
    size === "medium" ? "w-12 h-12" : "w-10 h-10";
  const textClasses =
    size === "medium" ? "text-xl" : "text-lg";

  // Ambil inisial jika tidak ada gambar
  const initials =
    name
      ?.split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "?";

  return (
    <View
      className={`
        ${sizeClasses}
        rounded-full bg-neutral-700 
        justify-center items-center overflow-hidden
      `}
    >
      {source ? (
        <Image source={{ uri: source }} className="w-full h-full" />
      ) : (
        <Text className={`${textClasses} text-white font-bold`}>
          {initials}
        </Text>
      )}
    </View>
  );
}