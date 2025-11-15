// src/features/canvas/components/BlockRenderer.tsx
import React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import Svg, { Rect, Circle, Path } from 'react-native-svg';
import type { Block } from '../../../types/canvas.types';
import { theme } from '@config/theme';

interface BlockRendererProps {
  block: Block;
  isSelected: boolean;
  onPress: () => void;
}

export const BlockRenderer: React.FC<BlockRendererProps> = ({ block, isSelected, onPress }) => {
  const renderContent = () => {
    switch (block.type) {
      case 'text':
        return (
          <Text style={styles.text}>
            {block.content?.text || 'Empty text block'}
          </Text>
        );
      
      case 'heading':
        return (
          <Text style={styles.heading}>
            {block.content?.text || 'Empty heading'}
          </Text>
        );
      
      case 'shape':
        return (
          <Svg width={block.size.width} height={block.size.height}>
            {block.content?.shape === 'circle' ? (
              <Circle
                cx={block.size.width / 2}
                cy={block.size.height / 2}
                r={Math.min(block.size.width, block.size.height) / 2 - 2}
                fill={block.content?.fill || '#3b82f6'}
                stroke={isSelected ? theme.colors.primary : '#e5e7eb'}
                strokeWidth={isSelected ? 3 : 1}
              />
            ) : (
              <Rect
                x={1}
                y={1}
                width={block.size.width - 2}
                height={block.size.height - 2}
                fill={block.content?.fill || '#3b82f6'}
                stroke={isSelected ? theme.colors.primary : '#e5e7eb'}
                strokeWidth={isSelected ? 3 : 1}
                rx={4}
              />
            )}
          </Svg>
        );
      
      case 'code':
        return (
          <Text style={styles.code}>
            {block.content?.code || '// Empty code block'}
          </Text>
        );
      
      default:
        return <Text style={styles.text}>Unknown block type: {block.type}</Text>;
    }
  };

  return (
    <View
      style={[
        styles.container,
        {
          left: block.position.x,
          top: block.position.y,
          width: block.size.width,
          height: block.size.height,
        },
        isSelected && styles.selected,
      ]}
      onTouchEnd={onPress}
    >
      {renderContent()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.sm,
    ...Platform.select({
      web: { boxShadow: '0 2px 4px rgba(0,0,0,0.10)' },
      default: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
      },
    }),
  },
  selected: {
    borderColor: theme.colors.primary,
    borderWidth: 2,
    ...(Platform.OS === 'web'
      ? { boxShadow: '0 2px 6px rgba(0,0,0,0.20)' }
      : { shadowOpacity: 0.2 }),
  },
  text: {
    fontSize: theme.fontSize.md,
    color: theme.colors.text,
  },
  heading: {
    fontSize: theme.fontSize.xl,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  code: {
    fontSize: theme.fontSize.sm,
    fontFamily: 'monospace',
    color: theme.colors.text,
    backgroundColor: '#f3f4f6',
    padding: theme.spacing.xs,
    borderRadius: 4,
  },
});
