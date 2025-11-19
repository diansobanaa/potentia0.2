import React from 'react';
import { useLocalSearchParams } from 'expo-router';
import SharedChat from '@/src/features/chat/ui/SharedChat';

export default function ConversationChatScreen() {
  const { conversation_id } = useLocalSearchParams<{ conversation_id?: string }>();
  return <SharedChat conversationId={conversation_id ?? null} />;
}