import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import { 
  View, Text, StyleSheet, TextInput, TouchableOpacity, FlatList,
  KeyboardAvoidingView, Platform, ActivityIndicator,
  NativeSyntheticEvent, NativeScrollEvent, ListRenderItem, Keyboard, LayoutChangeEvent
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { MarkdownText } from '@/src/shared/ui/MarkdownText';
import { useChatStore } from '@/src/features/chat/store';
import { HiTLApprovalCard } from '@/src/features/chat/ui/HiTLApprovalCard';
import type { Message } from '@/src/features/chat/types';

// --- PARSER BARU (Streaming Friendly) ---
// Logic: Deteksi tag pembuka. Jika ada, ambil isinya. 
// Jika tag penutup belum ada (masih ngetik), anggap sisa string sbg reasoning.
const splitReasoningBlocks = (text: string) => {
  if (!text) return [];
  
  const result: Array<{ type: 'reasoning' | 'text', content: string }> = [];
  const openTagRegex = /(<tkD>|<thinkingDiv>)/i;
  const closeTagRegex = /(<\/tkD>|<\/thinkingDiv>)/i;

  let remaining = text;

  while (remaining.length > 0) {
    const openMatch = openTagRegex.exec(remaining);

    // 1. Jika tidak ada tag pembuka lagi, sisanya adalah teks biasa
    if (!openMatch) {
      if (remaining.trim()) result.push({ type: 'text', content: remaining });
      break;
    }

    // 2. Ambil teks SEBELUM tag pembuka (jika ada)
    if (openMatch.index > 0) {
      const preText = remaining.slice(0, openMatch.index);
      if (preText.trim()) result.push({ type: 'text', content: preText });
    }

    // 3. Proses isi Reasoning
    // Potong string sampai setelah tag pembuka
    const contentStartIndex = openMatch.index + openMatch[0].length;
    remaining = remaining.slice(contentStartIndex);

    const closeMatch = closeTagRegex.exec(remaining);

    if (closeMatch) {
      // Kasus A: Block sudah selesai (ada tag penutup)
      const reasoningContent = remaining.slice(0, closeMatch.index);
      if (reasoningContent.trim()) {
        result.push({ type: 'reasoning', content: reasoningContent });
      }
      // Lanjut parsing sisanya setelah tag penutup
      remaining = remaining.slice(closeMatch.index + closeMatch[0].length);
    } else {
      // Kasus B: Block BELUM selesai (Streaming sedang jalan)
      // Anggap semua sisa string saat ini adalah bagian dari reasoning
      if (remaining.trim()) {
        result.push({ type: 'reasoning', content: remaining });
      }
      break; // Tidak ada lagi yang bisa diparse
    }
  }

  return result;
};

// --- COMPONENTS ---

// 1. Thinking Block (Footer)
const ThinkingBlock = ({ status }: { status: string }) => (
  <View style={styles.thinkingContainer}>
    <View style={styles.thinkingBubble}>
      <ActivityIndicator size="small" color="#1d9bf0" />
      <Text style={styles.thinkingText}>{status || 'AI is thinking...'}</Text>
    </View>
  </View>
);

// 2. Streaming Bubble (Pesan yang sedang diketik)
const StreamingBubble = ({ content }: { content: string }) => {
  if (!content) return null;
  
  // Gunakan parser yang sama agar saat streaming pun reasoning block terlihat
  const blocks = splitReasoningBlocks(content);

  return (
    <View style={[styles.messageBubble, styles.assistantBubble]}>
       {blocks.map((block, i) => {
         if (block.type === 'reasoning') {
           // Saat streaming, kita bisa paksa expand reasoning agar terlihat prosesnya
           return (
             <View key={i} style={styles.reasoningContainer}>
               <View style={styles.reasoningToggle}>
                  <Text style={styles.reasoningToggleText}>Thinking Process...</Text>
                  <ActivityIndicator size="small" color="#10b981" />
               </View>
               <MarkdownText style={styles.reasoningText}>{block.content}</MarkdownText>
             </View>
           );
         }
         return <MarkdownText key={i} style={styles.messageContent}>{block.content}</MarkdownText>;
       })}
    </View>
  );
};

// 3. Chat Item (Pesan Permanen)
const ChatItem = React.memo(({ item }: { item: Message }) => {
  // Default expanded jika pesan masih baru (opsional)
  const [isReasoningOpen, setIsReasoningOpen] = useState(false); 
  const toggleReasoning = () => setIsReasoningOpen(p => !p);

  if (item.approvalRequest) {
    return <View style={{ marginBottom: 12 }}><Text style={{color:'gray'}}>Approval Request</Text></View>;
  }

  const blocks = useMemo(() => splitReasoningBlocks(item.content), [item.content]);
  const hasReasoning = blocks.some(b => b.type === 'reasoning');

  return (
    <View style={[styles.messageBubble, item.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
      {hasReasoning && (
        <TouchableOpacity onPress={toggleReasoning} style={styles.reasoningToggle}>
          <Text style={styles.reasoningToggleText}>{isReasoningOpen ? 'Hide Reasoning' : 'Show Reasoning'}</Text>
          <Ionicons name={isReasoningOpen ? 'chevron-up' : 'chevron-down'} size={16} color="#10b981" />
        </TouchableOpacity>
      )}
      
      {blocks.map((block, i) => {
        if (block.type === 'reasoning') {
           if (!isReasoningOpen) return null; // Hide jika closed
           return (
            <View key={i} style={styles.reasoningContainer}>
              <MarkdownText style={styles.reasoningText}>{block.content}</MarkdownText>
            </View>
           );
        }
        return <MarkdownText key={i} style={styles.messageContent}>{block.content}</MarkdownText>;
      })}
    </View>
  );
}, (prev, next) => prev.item.id === next.item.id && prev.item.content === next.item.content);


// --- MAIN COMPONENT ---
function SharedChat({ conversationId }: { conversationId: string | null }) {
  const { 
    messages, activeConversationId, streamingMessage, streamingStatus, 
    approvalRequest, isLoading, 
    loadMessages, sendMessage, setActiveConversation, approveTool, rejectTool 
  } = useChatStore();

  const [inputText, setInputText] = useState('');
  const flatListRef = useRef<FlatList>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  
  const scrollYRef = useRef(0);
  const contentHeightRef = useRef(0);
  const listHeightRef = useRef(0);
  const isUserDragging = useRef(false);

  useEffect(() => {
    setActiveConversation(conversationId);
    if (conversationId) {
      loadMessages(conversationId);
    }
  }, [conversationId]);

  const currentMessages = activeConversationId ? (messages[activeConversationId] || []) : [];

  useEffect(() => {
    const sub = Keyboard.addListener('keyboardDidShow', () => {
      const distanceFromBottom = contentHeightRef.current - listHeightRef.current - scrollYRef.current;
      if (distanceFromBottom < 500) {
        flatListRef.current?.scrollToEnd({ animated: true });
        setIsAtBottom(true);
      }
    });
    return () => sub.remove();
  }, []);

  const handleSend = () => {
    if (!inputText.trim() || isLoading) return;
    sendMessage(inputText);
    setInputText('');
    setIsAtBottom(true);
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const handleContentSizeChange = (w: number, h: number) => {
    contentHeightRef.current = h;
    if ((isAtBottom || isLoading || streamingMessage) && !isUserDragging.current) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  };

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { layoutMeasurement, contentOffset, contentSize } = e.nativeEvent;
    scrollYRef.current = contentOffset.y;
    const isClose = layoutMeasurement.height + contentOffset.y >= contentSize.height - 50;
    setIsAtBottom(isClose);
    setShowScrollButton(!isClose);
  };

  const renderItem: ListRenderItem<Message> = useCallback(({ item }) => <ChatItem item={item} />, []);

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      
      <FlatList
        ref={flatListRef}
        data={currentMessages}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        
        onContentSizeChange={handleContentSizeChange}
        onLayout={(e) => listHeightRef.current = e.nativeEvent.layout.height}
        onScroll={handleScroll}
        onScrollBeginDrag={() => isUserDragging.current = true}
        onScrollEndDrag={() => isUserDragging.current = false}
        scrollEventThrottle={32}
        
        removeClippedSubviews={true}
        initialNumToRender={15}
        maxToRenderPerBatch={10}
        windowSize={10}
        
        contentContainerStyle={styles.messagesContent}
        
        ListFooterComponent={
          <View>
            {/* 1. Streaming Bubble (Sedang Diketik) */}
            {streamingMessage ? <StreamingBubble content={streamingMessage} /> : null}

            {/* 2. Approval Card */}
            {approvalRequest ? (
               <View style={{ marginVertical: 10 }}>
                 <HiTLApprovalCard 
                    data={approvalRequest} 
                    onApprove={() => approveTool()} 
                    onDeny={() => rejectTool()} 
                 />
               </View>
            ) : null}

            {/* 3. Thinking (Hanya jika belum ada teks) */}
            {(isLoading && !streamingMessage && !approvalRequest) || (streamingStatus && !streamingMessage && !approvalRequest) ? (
              <ThinkingBlock status={streamingStatus} />
            ) : null}
          </View>
        }
      />

      {showScrollButton && (
        <TouchableOpacity style={styles.scrollToBottomBtn} onPress={() => { setIsAtBottom(true); flatListRef.current?.scrollToEnd({ animated: true }); }}>
          <Ionicons name="arrow-down" size={20} color="white" />
          {(isLoading || streamingMessage) && <View style={styles.newMsgBadge} />}
        </TouchableOpacity>
      )}

      <View style={styles.inputContainer}>
        <TextInput 
          style={styles.input} 
          value={inputText} 
          onChangeText={setInputText} 
          placeholder="Ketik pesan..." 
          placeholderTextColor="#71767b"
          multiline
          editable={!isLoading && !streamingMessage} 
        />
        <TouchableOpacity 
          style={[styles.sendButton, (!inputText.trim() || isLoading) && { opacity: 0.5 }]} 
          onPress={handleSend}
          disabled={!inputText.trim() || isLoading}
        >
          <Ionicons name="send" size={20} color={inputText.trim() ? "#1d9bf0" : "#71767b"} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

export default SharedChat;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  messagesContent: { padding: 16, gap: 12, paddingBottom: 30 },
  
  messageBubble: { padding: 12, borderRadius: 16, maxWidth: '85%' },
  userBubble: { alignSelf: 'flex-end', backgroundColor: '#1d9bf0' },
  assistantBubble: { alignSelf: 'flex-start', backgroundColor: '#2f3336' },
  messageContent: { color: '#fff', fontSize: 15, lineHeight: 22 },
  
  reasoningContainer: { backgroundColor: 'rgba(16, 185, 129, 0.1)', borderRadius: 8, padding: 8, marginTop: 4, borderLeftWidth: 2, borderColor: '#10b981' },
  reasoningToggle: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  reasoningToggleText: { color: '#10b981', fontSize: 12, fontWeight: '600', marginRight: 4 },
  reasoningText: { color: '#6ee7b7', fontSize: 12, fontStyle: 'italic' },
  
  thinkingContainer: { paddingVertical: 12, alignItems: 'flex-start', marginBottom: 10 },
  thinkingBubble: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#16181c', padding: 12, borderRadius: 20, gap: 10, borderWidth: 1, borderColor: '#2f3336' },
  thinkingText: { color: '#71767b', fontStyle: 'italic', fontSize: 14 },

  inputContainer: { flexDirection: 'row', padding: 12, borderTopWidth: 1, borderColor: '#2f3336', alignItems: 'flex-end', gap: 8, backgroundColor: '#000' },
  input: { flex: 1, backgroundColor: '#2f3336', borderRadius: 20, padding: 12, color: '#fff', maxHeight: 100 },
  sendButton: { padding: 10, backgroundColor: '#2f3336', borderRadius: 20 },
  
  scrollToBottomBtn: { position: 'absolute', bottom: 80, right: 20, backgroundColor: '#1d9bf0', width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center', zIndex: 50, elevation: 5 },
  newMsgBadge: { position: 'absolute', top: 0, right: 0, width: 10, height: 10, borderRadius: 5, backgroundColor: 'red' }
});