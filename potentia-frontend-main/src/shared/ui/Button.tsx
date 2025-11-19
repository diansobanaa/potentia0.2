// Lokasi: src/shared/ui/Button.tsx

import { TouchableOpacity, Text, TouchableOpacityProps, StyleSheet } from "react-native";

export interface ButtonProps extends TouchableOpacityProps {
  title: string;
  variant?: "primary" | "outline";
}

export function Button({
  variant = "primary",
  title,
  disabled,
  style,
  ...props
}: ButtonProps) {
  const buttonStyle = [
    styles.base,
    variant === "primary" ? styles.primary : styles.outline,
    disabled && styles.disabled,
    style,
  ];

  const textStyle = [
    styles.text,
    variant === "primary" ? styles.textPrimary : styles.textOutline,
    disabled && styles.textDisabled,
  ];

  return (
    <TouchableOpacity
      style={buttonStyle}
      disabled={disabled}
      activeOpacity={0.7}
      {...props}
    >
      <Text style={textStyle}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 9999,
    paddingVertical: 16,
  },
  primary: {
    backgroundColor: '#ffffff',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#404040',
  },
  disabled: {
    backgroundColor: '#404040',
  },
  text: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  textPrimary: {
    color: '#000000',
  },
  textOutline: {
    color: '#ffffff',
  },
  textDisabled: {
    color: '#a3a3a3',
  },
});