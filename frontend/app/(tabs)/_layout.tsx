// app/(tabs)/_layout.tsx
import { Tabs } from 'expo-router';
import { theme } from '@config/theme';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.textSecondary,
        headerShown: true,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarLabel: 'Home',
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'AI Assistant',
          tabBarLabel: 'Chat',
        }}
      />
      <Tabs.Screen
        name="canvas"
        options={{
          title: 'Canvas',
          tabBarLabel: 'Canvas',
        }}
      />
    </Tabs>
  );
}
