// Lokasi: src/shared/ui/TabBarIcon.tsx


import React from "react";
import { Ionicons } from "@expo/vector-icons";

interface TabBarIconProps {
  name: React.ComponentProps<typeof Ionicons>["name"];
  color: string;
  focused: boolean;
}

export const TabBarIcon = React.forwardRef<any, TabBarIconProps>(
  function TabBarIcon({ name, color, focused }, ref) {
    const iconName = focused ? name : (`${name}-outline` as any);
    return <Ionicons ref={ref} size={26} name={iconName} color={color} />;
  }
);