// src/features/canvas/components/CanvasToolbar.tsx
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { theme } from '@config/theme';
import type { Block } from '../../../types/canvas.types';

interface CanvasToolbarProps {
  onAddBlock: (type: Block['type']) => void;
  isConnected: boolean;
  selectedCount: number;
  onDelete?: () => void;
}

export const CanvasToolbar: React.FC<CanvasToolbarProps> = ({
  onAddBlock,
  isConnected,
  selectedCount,
  onDelete,
}) => {
  const tools = [
    { type: 'text' as const, label: 'Text', icon: 'T' },
    { type: 'heading' as const, label: 'Heading', icon: 'H' },
    { type: 'shape' as const, label: 'Shape', icon: '⬜' },
    { type: 'code' as const, label: 'Code', icon: '</>' },
  ];

  return (
    <View style={styles.container}>
      {/* Connection status */}
      <View style={styles.status}>
        <View style={[styles.dot, isConnected ? styles.connected : styles.disconnected]} />
        <Text style={styles.statusText}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </Text>
      </View>

      {/* Tools */}
      <View style={styles.tools}>
        {tools.map((tool) => (
          <TouchableOpacity
            key={tool.type}
            style={styles.tool}
            onPress={() => onAddBlock(tool.type)}
            disabled={!isConnected}
          >
            <Text style={styles.toolIcon}>{tool.icon}</Text>
            <Text style={styles.toolLabel}>{tool.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Selection actions */}
      {selectedCount > 0 && (
        <View style={styles.actions}>
          <Text style={styles.selectionText}>{selectedCount} selected</Text>
          {onDelete && (
            <TouchableOpacity style={styles.deleteButton} onPress={onDelete}>
              <Text style={styles.deleteText}>Delete</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  status: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  connected: {
    backgroundColor: '#10b981',
  },
  disconnected: {
    backgroundColor: '#ef4444',
  },
  statusText: {
    fontSize: theme.fontSize.sm,
    color: theme.colors.textSecondary,
  },
  tools: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  tool: {
    alignItems: 'center',
    padding: theme.spacing.xs,
    borderRadius: 8,
    backgroundColor: theme.colors.background,
    minWidth: 60,
  },
  toolIcon: {
    fontSize: 20,
    marginBottom: 2,
  },
  toolLabel: {
    fontSize: theme.fontSize.xs,
    color: theme.colors.text,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
  },
  selectionText: {
    fontSize: theme.fontSize.sm,
    color: theme.colors.text,
  },
  deleteButton: {
    backgroundColor: '#ef4444',
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: 6,
  },
  deleteText: {
    color: '#fff',
    fontSize: theme.fontSize.sm,
    fontWeight: '600',
  },
});
