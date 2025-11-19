import React from 'react';
import { KeyboardAvoidingView, Platform } from 'react-native';
import SharedChat from '@/src/features/chat/ui/SharedChat';

export default function ChatScreen() {
  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={100}>
      <SharedChat conversationId={null} />
    </KeyboardAvoidingView>
  );
}