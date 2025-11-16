// Lokasi: src/features/auth/ui/SocialButton.tsx

import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  Image,
} from "react-native";

type IconName = "google" | "apple";

const icons = {
  google: "[https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg](https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg)",
  apple: "[https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg](https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg)",
};

interface SocialButtonProps {
  icon: IconName;
  text: string;
  onPress: () => void;
  isLoading?: boolean; // <-- Prop baru
}

export function SocialButton({
  icon,
  text,
  onPress,
  isLoading = false,
}: SocialButtonProps) {
  return (
    <TouchableOpacity
      className={`
        w-full flex-row justify-center items-center 
        bg-white rounded-full py-4 space-x-2
        active:bg-neutral-200
        ${isLoading ? "opacity-70" : ""}
      `}
      onPress={onPress}
      disabled={isLoading}
    >
      {isLoading ? (
        <ActivityIndicator size="small" color="#000000" />
      ) : (
        <Image
          source={{ uri: icons[icon] }}
          className={`w-6 h-6 ${icon === "apple" ? "tint-black" : ""}`}
        />
      )}
      <Text className="text-black text-lg font-bold">{text}</Text>
    </TouchableOpacity>
  );
}