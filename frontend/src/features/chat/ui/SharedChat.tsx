
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { MarkdownText } from '@/src/shared/ui/MarkdownText';
import { useAuthUser } from '@/src/features/auth/store';
import { supabase } from '@/src/shared/api/supabase';
import { env } from '@/src/shared/config/env';

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  modelBar: { paddingHorizontal: 12, paddingTop: 8, paddingBottom: 4, borderBottomWidth: 1, borderBottomColor: '#2f3336', backgroundColor: '#000' },
  modelButton: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#0b1620', borderWidth: 1, borderColor: '#1d9bf0', borderRadius: 999 },
  modelText: { color: '#1d9bf0', fontSize: 12, fontWeight: '600' },
  modelMenu: { marginTop: 6, backgroundColor: '#111827', borderWidth: 1, borderColor: '#374151', borderRadius: 8, paddingVertical: 4, width: 240 },
  modelMenuItem: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 12, paddingVertical: 8 },
  modelMenuItemActive: { backgroundColor: 'rgba(16,185,129,0.1)' },
  modelMenuText: { color: '#e5e7eb', fontSize: 13 },
  messagesContainer: { flex: 1 },
  messagesContent: { padding: 16, gap: 12 },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 100 },
  emptyTitle: { color: '#fff', fontSize: 24, fontWeight: '700', marginTop: 16 },
  emptySubtitle: { color: '#71767b', fontSize: 15, marginTop: 8, textAlign: 'center' },
  messageBubble: { padding: 12, borderRadius: 16, marginBottom: 8, maxWidth: '85%' },
  userBubble: { alignSelf: 'flex-end', backgroundColor: '#1d9bf0' },
  assistantBubble: { alignSelf: 'flex-start', backgroundColor: '#77797b24' },
  messageHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  messageRole: { color: '#fff', fontSize: 13, fontWeight: '600' },
  messageContent: { color: '#fff', fontSize: 11, lineHeight: 16, fontStyle: 'italic' },
  inputContainer: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, borderTopWidth: 1, borderTopColor: '#2f3336', backgroundColor: '#000', gap: 8 },
  input: { flex: 1, backgroundColor: '#2f3336', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, color: '#fff', fontSize: 15, maxHeight: 100 },
  sendButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#2f3336', justifyContent: 'center', alignItems: 'center' },
  sendButtonDisabled: { opacity: 0.5 },
  reasoningContainer: {
    borderRadius: 8,
    paddingLeft: 12,
    borderLeftWidth: 2,
    borderLeftColor: '#305c4dff'
  },
  reasoningLabel: { color: '#30886b75', fontSize: 14, fontWeight: '500', marginBottom: 4 },
  reasoningToggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8, paddingHorizontal: 12 },
  reasoningToggleText: { color: '#10b981', fontSize: 12, fontWeight: '500' },
  reasoningText: {
    color: '#30886b',
    fontSize: 10,
    lineHeight: 15,
    fontWeight: '400',
    fontStyle: 'italic',
  },
  loadingBubble: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 8 },
  loadingText: { color: '#fff', fontSize: 13 },
});

interface UsageInfo {
  input_tokens?: number;
  output_tokens?: number;
  cost?: number;
  model?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  usage?: UsageInfo;
  timestamp: Date;
}


interface SharedChatProps {
  conversationId: string | null;
}

// Module-level variable to cache models and prevent multiple fetches per app session
let cachedModels: string[] | null = null;
let hasFetchedModels = false;

function SharedChat({ conversationId }: SharedChatProps) {
  const user = useAuthUser();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showThinking, setShowThinking] = useState<{ [key: string]: boolean }>({});
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [modelMenuOpen, setModelMenuOpen] = useState<boolean>(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(false);
  const [hasMore, setHasMore] = useState(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const [reasoningOpen, setReasoningOpen] = useState<{ [id: string]: boolean }>({});
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const scrollViewRef = useRef<ScrollView>(null);
  const PAGE_SIZE = 10;
  const isFetchingRef = useRef(false);

  // Fetch available models from API
  useEffect(() => {
    if (hasFetchedModels && cachedModels) {
      setAvailableModels(cachedModels);
      if (!selectedModel && cachedModels.length > 0) {
        setSelectedModel(cachedModels[0]);
      }
      return;
    }
    const fetchModels = async () => {
      try {
        console.log('[MODEL_FETCH] Fetching available models from endpoint...');
        const token = await getAccessToken();
        const url = `${env.API_URL}/api/v1/chat/models/available`;
        const res = await fetch(url, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to fetch models');
        const data = await res.json();
        if (Array.isArray(data.available_models)) {
          cachedModels = data.available_models;
          hasFetchedModels = true;
          setAvailableModels(data.available_models);
          if (!selectedModel && data.available_models.length > 0) {
            setSelectedModel(data.available_models[0]);
          }
        }
      } catch (e) {
        setAvailableModels([]);
        console.error('Failed to fetch available models:', e);
      }
    };
    fetchModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [env.API_URL]);

  // Fetch chat history if conversationId exists
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      setIsHistoryLoading(false);
      return;
    }
    setIsHistoryLoading(true);
    const fetchHistory = async () => {
      try {
        const token = await getAccessToken();
        const url = `${env.API_URL}/api/v1/chat/${conversationId}/messages?limit=${PAGE_SIZE}&offset=0`;
        console.log('[DEBUG] Fetching chat history from:', url);
        const res = await fetch(url, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`Failed to load history: ${res.status} - ${errText}`);
        }
        const data = await res.json();
        // Pastikan ambil dari data.items jika ada
        const hydrated: Message[] = (data.items || data || []).map((m: any, idx: number) => ({
          id: m.id ? String(m.id) : `${Date.now()}-${idx}`,
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content || '',
          thinking: m.thinking,
          usage: m.usage,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
        }));
        // Urutkan pesan dari yang paling lama ke paling baru
        hydrated.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
        setMessages(hydrated);
      } catch (e) {
        setMessages([]);
        console.error('Load history error:', e);
      } finally {
        setIsHistoryLoading(false);
      }
    };
    fetchHistory();
  }, [conversationId]);

  const getAccessToken = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      return session?.access_token || '';
    } catch (error) {
      console.error('Failed to get access token:', error);
      return '';
    }
  };

  // --- Reasoning block parser: split content into reasoning container and normal text ---
  function splitReasoningBlocks(text: string): Array<{ type: 'reasoning' | 'text', content: string }> {
    const regex = /(<tkD>|<thinkingDiv>)([\s\S]*?)(<\/tkD>|<\/thinkingDiv>)/gi;
    let result: Array<{ type: 'reasoning' | 'text', content: string }> = [];
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        result.push({ type: 'text', content: text.slice(lastIndex, match.index) });
      }
      result.push({ type: 'reasoning', content: match[2].trim() });
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      result.push({ type: 'text', content: text.slice(lastIndex) });
    }
    return result.filter(b => b.content.trim() !== '');
  }

  const handleToggleReasoning = useCallback((id: string) => {
    setReasoningOpen(prev => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // UI rendering (simplified, can be expanded as needed)

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={100}>
      <View style={styles.modelBar}>
        <TouchableOpacity onPress={() => setModelMenuOpen(v => !v)} style={styles.modelButton} activeOpacity={0.8}>
          <Ionicons name="options-outline" size={16} color="#1d9bf0" />
          <Text style={styles.modelText}>{selectedModel}</Text>
          <Ionicons name={modelMenuOpen ? 'chevron-up' : 'chevron-down'} size={14} color="#71767b" />
        </TouchableOpacity>
        {modelMenuOpen && (
          <View style={styles.modelMenu}>
            {availableModels.length === 0 ? (
              <Text style={{ color: '#fff', padding: 12 }}>Memuat model...</Text>
            ) : (
              availableModels.map(m => (
                <TouchableOpacity key={m} style={[styles.modelMenuItem, selectedModel === m && styles.modelMenuItemActive]} onPress={() => { setSelectedModel(m); setModelMenuOpen(false); }}>
                  <Text style={styles.modelMenuText}>{m}</Text>
                  {selectedModel === m && <Ionicons name="checkmark" size={14} color="#10b981" />}
                </TouchableOpacity>
              ))
            )}
          </View>
        )}
        {isHistoryLoading && (
          <View style={styles.loadingBubble}>
            <ActivityIndicator size='small' color='#1d9bf0' />
            <Text style={styles.loadingText}>Memuat riwayat chat...</Text>
          </View>
        )}
      </View>
      <ScrollView
        ref={scrollViewRef}
        style={styles.messagesContainer}
        contentContainerStyle={styles.messagesContent}
        showsVerticalScrollIndicator={false}
      >
        {!conversationId ? (
          <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={64} color="#71767b" />
            <Text style={styles.emptyTitle}>Mulai Percakapan</Text>
            <Text style={styles.emptySubtitle}>Tanyakan apa saja kepada AI Assistant</Text>
          </View>
        ) : (
          messages.map(message => {
            const blocks = splitReasoningBlocks(message.content);
            const hasReasoning = blocks.some(b => b.type === 'reasoning');

            return (
              <View key={message.id} style={[styles.messageBubble, message.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
                {hasReasoning && (
                  <TouchableOpacity onPress={() => handleToggleReasoning(message.id)} style={styles.reasoningToggle}>
                    <Text style={styles.reasoningToggleText}>
                      {reasoningOpen[message.id] ? 'Reasoning' : 'Reasoning'}
                    </Text>
                    <Ionicons name={reasoningOpen[message.id] ? 'chevron-up' : 'chevron-down'} size={16} color="#10b981" />
                  </TouchableOpacity>
                )}
                {hasReasoning && reasoningOpen[message.id] && (
                  <View style={styles.reasoningContainer}>
                    {blocks.filter(b => b.type === 'reasoning').map((block, i) => (
                      <MarkdownText key={i} style={styles.reasoningText}>{block.content}</MarkdownText>
                    ))}
                  </View>
                )}
                {/* Main message content (text blocks only) */}
                {blocks.filter(b => b.type === 'text').map((block, i) => (
                  <MarkdownText key={i} style={styles.messageContent}>{block.content}</MarkdownText>
                ))}
              </View>
            );
          })
        )}
      </ScrollView>
      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="Ketik pesan..." placeholderTextColor="#71767b" value={inputText} onChangeText={setInputText} multiline maxLength={2000} editable={!isLoading} />
        <TouchableOpacity style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]} /* onPress={handleSend} */ disabled={!inputText.trim() || isLoading}>
          <Ionicons name="send" size={20} color={inputText.trim() && !isLoading ? '#1d9bf0' : '#71767b'} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

export default SharedChat;
