// src/features/chat/components/MessageBubble.tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '@config/theme';
import type { Message } from '@types/chat.types';

interface MessageBubbleProps {
  message: Message;
  isOwn?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isOwn }) => {
  const isUser = message.role === 'user' || isOwn;

  return (
    <View style={[
      styles.container,
      isUser ? styles.userContainer : styles.assistantContainer
    ]}>
      <View style={[
        styles.bubble,
        isUser ? styles.userBubble : styles.assistantBubble
      ]}>
        <Text style={[
          styles.content,
          isUser ? styles.userText : styles.assistantText
        ]}>
          {message.content}
        </Text>
        
        {message.metadata?.tokens && (
          <Text style={styles.metadata}>
            Tokens: {message.metadata.tokens.input + message.metadata.tokens.output}
          </Text>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: theme.spacing.xs,
    paddingHorizontal: theme.spacing.md,
  },
  userContainer: {
    alignItems: 'flex-end',
  },
  assistantContainer: {
    alignItems: 'flex-start',
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
  },
  userBubble: {
    backgroundColor: theme.colors.primary,
  },
  assistantBubble: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  content: {
    fontSize: theme.fontSize.md,
  },
  userText: {
    color: '#ffffff',
  },
  assistantText: {
    color: theme.colors.text,
  },
  metadata: {
    fontSize: theme.fontSize.xs,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
});
