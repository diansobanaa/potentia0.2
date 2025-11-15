// app/(tabs)/canvas.tsx
import React from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@components/ui';
import { theme } from '@config/theme';

export default function CanvasTabScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Collaborative Canvas</Text>
        <Text style={styles.subtitle}>
          Create and edit visual canvases in real-time with your team
        </Text>

        <View style={styles.actions}>
          <Button onPress={() => router.push('/canvas')}>
            View My Canvases
          </Button>
        </View>

        <View style={styles.features}>
          <Text style={styles.featureTitle}>Features:</Text>
          <Text style={styles.feature}>✓ Real-time collaboration</Text>
          <Text style={styles.feature}>✓ Multiple block types (text, shapes, code)</Text>
          <Text style={styles.feature}>✓ Live cursor presence</Text>
          <Text style={styles.feature}>✓ Drag and pan viewport</Text>
          <Text style={styles.feature}>✓ WebSocket sync with backend</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    flex: 1,
    padding: theme.spacing.lg,
    justifyContent: 'center',
  },
  title: {
    fontSize: theme.fontSize.xxl,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: theme.fontSize.md,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xl,
    textAlign: 'center',
  },
  actions: {
    marginBottom: theme.spacing.xl,
  },
  features: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.lg,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  featureTitle: {
    fontSize: theme.fontSize.lg,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
  },
  feature: {
    fontSize: theme.fontSize.md,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
});
