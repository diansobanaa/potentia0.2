// app/(tabs)/index.tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useAuthStore } from '@features/auth/store/authStore';
import { Button } from '@components/ui';
import { theme } from '@config/theme';
import { router } from 'expo-router';

export default function HomeScreen() {
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    router.replace('/(auth)/login');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Welcome, {user?.full_name || 'User'}!</Text>
      <Text style={styles.subtitle}>Tier: {user?.subscription_tier || 'free'}</Text>

      <View style={styles.actions}>
        <Button onPress={() => router.push('/chat')}>
          Go to AI Chat
        </Button>
        
        <Button 
          onPress={handleLogout} 
          variant="secondary"
          style={styles.logoutButton}
        >
          Logout
        </Button>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: theme.spacing.lg,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background,
  },
  title: {
    fontSize: theme.fontSize.xxl,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  subtitle: {
    fontSize: theme.fontSize.md,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xl,
  },
  actions: {
    width: '100%',
    maxWidth: 300,
  },
  logoutButton: {
    marginTop: theme.spacing.md,
  },
});
