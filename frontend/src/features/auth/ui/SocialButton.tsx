// Lokasi: src/features/auth/ui/SocialButton.tsx

import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  Image,
  StyleSheet,
} from "react-native";

type IconName = "google" | "apple";

const icons = {
  google: "https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg",
  apple: "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
};

interface SocialButtonProps {
  icon: IconName;
  text: string;
  onPress: () => void;
  isLoading?: boolean;
}

export function SocialButton({
  icon,
  text,
  onPress,
  isLoading = false,
}: SocialButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.button, isLoading && styles.buttonLoading]}
      onPress={onPress}
      disabled={isLoading}
      activeOpacity={0.7}
    >
      {isLoading ? (
        <ActivityIndicator size="small" color="#000000" />
      ) : (
        <Image
          source={{ uri: icons[icon] }}
          style={styles.icon}
        />
      )}
      <Text style={styles.text}>{text}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 9999,
    paddingVertical: 16,
    gap: 8,
  },
  buttonLoading: {
    opacity: 0.7,
  },
  icon: {
    width: 24,
    height: 24,
  },
  text: {
    color: '#000000',
    fontSize: 18,
    fontWeight: 'bold',
  },
});