// app/canvas/index.tsx
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { router } from 'expo-router';
import { canvasApi } from '@services/api/canvas.api';
import { Button } from '@components/ui';
import { theme } from '@config/theme';
import type { Canvas } from '@types/canvas.types'; // keep as is; alias resolution expected

export default function CanvasListScreen() {
  const [canvases, setCanvases] = useState<Canvas[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadCanvases();
  }, []);

  const loadCanvases = async () => {
    try {
      setIsLoading(true);
      const response = await canvasApi.listCanvases();
      setCanvases(response.items);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to load canvases');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCanvas = async () => {
    try {
      setIsCreating(true);
      const newCanvas = await canvasApi.createCanvas('Untitled Canvas');
      router.push(`/canvas/${newCanvas.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create canvas');
    } finally {
      setIsCreating(false);
    }
  };

  const handleOpenCanvas = (canvasId: string) => {
    router.push(`/canvas/${canvasId}`);
  };

  const renderCanvas = ({ item }: { item: Canvas }) => (
    <TouchableOpacity
      style={styles.canvasCard}
      onPress={() => handleOpenCanvas(item.id)}
    >
      <Text style={styles.canvasTitle}>{item.title}</Text>
      <Text style={styles.canvasDate}>
        Updated: {new Date(item.updated_at).toLocaleDateString()}
      </Text>
    </TouchableOpacity>
  );

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My Canvases</Text>
        <Button onPress={handleCreateCanvas} loading={isCreating}>
          + New Canvas
        </Button>
      </View>

      {canvases.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyText}>No canvases yet</Text>
          <Text style={styles.emptySubtext}>Create your first collaborative canvas</Text>
        </View>
      ) : (
        <FlatList
          data={canvases}
          renderItem={renderCanvas}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  title: {
    fontSize: theme.fontSize.xxl,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  list: {
    padding: theme.spacing.md,
  },
  canvasCard: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.lg,
    borderRadius: 12,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    ...Platform.select({
      web: { boxShadow: '0 2px 4px rgba(0,0,0,0.05)' },
      default: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
      },
    }),
  },
  canvasTitle: {
    fontSize: theme.fontSize.lg,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  canvasDate: {
    fontSize: theme.fontSize.sm,
    color: theme.colors.textSecondary,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.xl,
  },
  emptyText: {
    fontSize: theme.fontSize.lg,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  emptySubtext: {
    fontSize: theme.fontSize.md,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
});
