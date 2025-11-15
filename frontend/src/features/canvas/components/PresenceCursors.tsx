// src/features/canvas/components/PresenceCursors.tsx
import React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import type { CanvasPresence } from '../../../types/canvas.types';
import { theme } from '@config/theme';

interface PresenceCursorsProps {
  presence: Record<string, CanvasPresence>;
  viewport: { x: number; y: number; zoom: number };
}

export const PresenceCursors: React.FC<PresenceCursorsProps> = ({ presence, viewport }) => {
  return (
    <>
      {Object.values(presence).map((user) => {
        if (!user.cursor || user.status === 'offline') return null;

        const screenX = (user.cursor.x - viewport.x) * viewport.zoom;
        const screenY = (user.cursor.y - viewport.y) * viewport.zoom;

        return (
          <View
            key={user.user_id}
            style={[
              styles.cursor,
              {
                left: screenX,
                top: screenY,
              },
            ]}
          >
            <Svg width={24} height={24}>
              <Circle cx={12} cy={12} r={8} fill={user.color} opacity={0.8} />
            </Svg>
            <View style={[styles.nameTag, { backgroundColor: user.color }]}>
              <Text style={styles.name}>{user.user_name}</Text>
            </View>
          </View>
        );
      })}
    </>
  );
};

const styles = StyleSheet.create({
  cursor: {
    position: 'absolute',
    zIndex: 1000,
    pointerEvents: 'none',
  },
  nameTag: {
    position: 'absolute',
    top: 24,
    left: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    ...Platform.select({
      web: { boxShadow: '0 1px 2px rgba(0,0,0,0.20)' },
      default: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.2,
        shadowRadius: 2,
        elevation: 2,
      },
    }),
  },
  name: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
});
