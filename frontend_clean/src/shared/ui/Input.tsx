// Lokasi: src/shared/ui/Input.tsx

import { TextInput, View, Text, TextInputProps } from "react-native";

// Definisikan props tambahan yang mungkin kita butuhkan, seperti error
interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
}

export function Input({ label, error, ...props }: InputProps) {
  return (
    <View className="w-full">
      {label && (
        <Text className="text-white text-base font-medium mb-2">
          {label}
        </Text>
      )}
      
      <TextInput
        // Ini adalah styling inti ala "X"
        className={`
          w-full bg-black border border-neutral-700 text-white 
          text-lg rounded-md px-4 py-4
          focus:border-blue-500 focus:ring-blue-500 
          ${error ? "border-red-500" : ""}
        `}
        // Atur warna placeholder agar kontras
        placeholderTextColor="#71717a" // (Warna abu-abu/zinc-500)
        {...props}
      />
      
      {error && (
        <Text className="text-red-500 text-sm mt-1">
          {error}
        </Text>
      )}
    </View>
  );
}