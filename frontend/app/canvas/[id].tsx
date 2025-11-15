// app/canvas/[id].tsx
import React, { useEffect, useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Text,
  Dimensions,
  Alert,
} from 'react-native';
import { useLocalSearchParams, Stack } from 'expo-router';
import { GestureHandlerRootView, PanGestureHandler } from 'react-native-gesture-handler';
import { useCanvasStore } from '@features/canvas/store/canvasStore';
import {
  BlockRenderer,
  CanvasToolbar,
  PresenceCursors,
} from '@features/canvas/components';
import { theme } from '@config/theme';
import { useShallow } from 'zustand/react/shallow';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const CANVAS_WIDTH = 4000;
const CANVAS_HEIGHT = 4000;

export default function CanvasEditorScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });

  const {
    canvas,
    blocks,
    isConnected,
    isLoading,
    error,
    selectedBlocks,
    viewport,
    presence,
    connectToCanvas,
    disconnectFromCanvas,
    createBlock,
    selectBlock,
    clearSelection,
    deleteBlock,
    updateViewport,
    updateCursor,
  } = useCanvasStore(useShallow((state) => ({
    canvas: state.canvas,
    blocks: state.blocks,
    isConnected: state.isConnected,
    isLoading: state.isLoading,
    error: state.error,
    selectedBlocks: state.selectedBlocks,
    viewport: state.viewport,
    presence: state.presence,
    connectToCanvas: state.connectToCanvas,
    disconnectFromCanvas: state.disconnectFromCanvas,
    createBlock: state.createBlock,
    selectBlock: state.selectBlock,
    clearSelection: state.clearSelection,
    deleteBlock: state.deleteBlock,
    updateViewport: state.updateViewport,
    updateCursor: state.updateCursor,
  })));

  useEffect(() => {
    if (id) {
      connectToCanvas(id);
    }

    return () => {
      disconnectFromCanvas();
    };
  }, [id]);

  const handleAddBlock = (type: any) => {
    // Add block at center of viewport
    const centerX = viewport.x + SCREEN_WIDTH / 2 / viewport.zoom;
    const centerY = viewport.y + SCREEN_HEIGHT / 2 / viewport.zoom;
    createBlock(type, { x: centerX, y: centerY });
  };

  const handleDeleteSelected = () => {
    if (selectedBlocks.size === 0) return;

    Alert.alert(
      'Delete Blocks',
      `Delete ${selectedBlocks.size} block(s)?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            selectedBlocks.forEach((blockId) => deleteBlock(blockId));
            clearSelection();
          },
        },
      ]
    );
  };

  const handlePan = (event: any) => {
    const { translationX, translationY } = event.nativeEvent;
    setPanOffset({
      x: translationX,
      y: translationY,
    });
  };

  const handlePanEnd = () => {
    updateViewport({
      x: viewport.x - panOffset.x / viewport.zoom,
      y: viewport.y - panOffset.y / viewport.zoom,
    });
    setPanOffset({ x: 0, y: 0 });
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
        <Text style={styles.loadingText}>Connecting to canvas...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Error: {error}</Text>
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={styles.container}>
      <Stack.Screen
        options={{
          title: canvas?.title || 'Canvas',
          headerShown: true,
        }}
      />

      <CanvasToolbar
        onAddBlock={handleAddBlock}
        isConnected={isConnected}
        selectedCount={selectedBlocks.size}
        onDelete={selectedBlocks.size > 0 ? handleDeleteSelected : undefined}
      />

      <PanGestureHandler
        onGestureEvent={handlePan}
        onEnded={handlePanEnd}
      >
        <View style={styles.canvasContainer}>
          <View
            style={[
              styles.canvas,
              {
                width: CANVAS_WIDTH * viewport.zoom,
                height: CANVAS_HEIGHT * viewport.zoom,
                transform: [
                  { translateX: -viewport.x * viewport.zoom + panOffset.x },
                  { translateY: -viewport.y * viewport.zoom + panOffset.y },
                ],
              },
            ]}
          >
            {/* Render blocks */}
            {Object.values(blocks).map((block) => (
              <BlockRenderer
                key={block.id}
                block={block}
                isSelected={selectedBlocks.has(block.id)}
                onPress={() => selectBlock(block.id)}
              />
            ))}

            {/* Render presence cursors */}
            <PresenceCursors presence={presence} viewport={viewport} />
          </View>
        </View>
      </PanGestureHandler>
    </GestureHandlerRootView>
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
    backgroundColor: theme.colors.background,
  },
  loadingText: {
    marginTop: theme.spacing.md,
    fontSize: theme.fontSize.md,
    color: theme.colors.textSecondary,
  },
  errorText: {
    fontSize: theme.fontSize.md,
    color: '#ef4444',
    textAlign: 'center',
    paddingHorizontal: theme.spacing.lg,
  },
  canvasContainer: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: '#f9fafb',
  },
  canvas: {
    position: 'relative',
    backgroundColor: '#ffffff',
  },
});
