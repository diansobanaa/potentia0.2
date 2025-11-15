// app/(tabs)/chat.tsx
import React, { useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Text,
} from 'react-native';
import { useChatStore } from '@features/chat/store/chatStore';
import {
  MessageBubble,
  MessageInput,
  HiTLApprovalCard,
} from '@features/chat/components';
import { theme } from '@config/theme';
import { useShallow } from 'zustand/react/shallow';

export default function ChatScreen() {
  const {
    messages,
    activeConversationId,
    streamingMessage,
    streamingStatus,
    isLoading,
    approvalRequest,
    sendMessage,
    approveTool,
    rejectTool,
    loadMessages,
  } = useChatStore(useShallow((state) => ({
    messages: state.activeConversationId
      ? state.messages[state.activeConversationId] || []
      : [],
    activeConversationId: state.activeConversationId,
    streamingMessage: state.streamingMessage,
    streamingStatus: state.streamingStatus,
    isLoading: state.isLoading,
    approvalRequest: state.approvalRequest,
    sendMessage: state.sendMessage,
    approveTool: state.approveTool,
    rejectTool: state.rejectTool,
    loadMessages: state.loadMessages,
  })));

  // Load messages when conversation changes
  useEffect(() => {
    if (activeConversationId) {
      loadMessages(activeConversationId);
    }
  }, [activeConversationId]);

  const handleSend = (text: string) => {
    sendMessage(text, {
      model: 'gemini-2.5-flash',
      temperature: 0.2,
    });
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={100}
    >
      <ScrollView style={styles.messagesContainer}>
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming message */}
        {streamingMessage && (
          <View style={styles.streamingContainer}>
            <MessageBubble
              message={{
                id: 'streaming',
                conversation_id: activeConversationId || '',
                role: 'assistant',
                content: streamingMessage,
                created_at: new Date().toISOString(),
              }}
            />
          </View>
        )}

        {/* Status indicator */}
        {streamingStatus && (
          <Text style={styles.statusText}>{streamingStatus}</Text>
        )}
      </ScrollView>

      {/* Human-in-the-Loop Approval Card */}
      {approvalRequest && (
        <HiTLApprovalCard
          request={approvalRequest}
          onApprove={approveTool}
          onReject={rejectTool}
        />
      )}

      {/* Message Input */}
      <MessageInput
        onSend={handleSend}
        disabled={isLoading || !!approvalRequest}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  messagesContainer: {
    flex: 1,
    paddingVertical: theme.spacing.md,
  },
  streamingContainer: {
    opacity: 0.8,
  },
  statusText: {
    textAlign: 'center',
    color: theme.colors.textSecondary,
    fontSize: theme.fontSize.sm,
    paddingVertical: theme.spacing.sm,
    fontStyle: 'italic',
  },
});
