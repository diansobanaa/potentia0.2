// app/_layout.tsx
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { useAuthStore } from '@features/auth/store/authStore';
import { ErrorBoundary } from '@components/ErrorBoundary';

export default function RootLayout() {
  const loadUser = useAuthStore((state) => state.loadUser);

  useEffect(() => {
    // Load user from storage on app start
    loadUser();
  }, []);

  return (
    <ErrorBoundary>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </ErrorBoundary>
  );
}
