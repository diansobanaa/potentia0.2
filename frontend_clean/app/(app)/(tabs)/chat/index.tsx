import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuthUser } from '@/src/features/auth/store';
import { supabase } from '@/src/shared/api/supabase';
import { env } from '@/src/shared/config/env';
import { MarkdownText } from '@/src/shared/ui/MarkdownText';
import { useRouter } from 'expo-router';

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

export default function ChatScreen() {
  const user = useAuthUser();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showThinking, setShowThinking] = useState<{ [key: string]: boolean }>({});
  const [isThinking, setIsThinking] = useState<{ [key: string]: boolean }>({});
  const [selectedModel, setSelectedModel] = useState<string>('gemini-2.5-flash');
  const [modelMenuOpen, setModelMenuOpen] = useState<boolean>(false);
  const scrollViewRef = useRef<ScrollView>(null);

  const parseStreamingText = (text: string) => {
    const hasOpenTag = text.includes('<thinkingDiv>');
    const hasCloseTag = text.includes('</thinkingDiv>');
    if (hasOpenTag && hasCloseTag) {
      const thinkingRegex = /<thinkingDiv>(.*?)<\/thinkingDiv>/s;
      const match = text.match(thinkingRegex);
      if (match) {
        const thinking = match[1].trim();
        const content = text.replace(thinkingRegex, '').trim();
        return { thinking, content, isThinkingActive: false };
      }
    }
    if (hasOpenTag && !hasCloseTag) {
      const parts = text.split('<thinkingDiv>');
      const thinking = parts[1] || '';
      return { thinking, content: '', isThinkingActive: true };
    }
    return { thinking: undefined, content: text, isThinkingActive: false };
  };

  const toggleThinking = (messageId: string) => {
    setShowThinking(prev => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  const getAccessToken = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      return session?.access_token || '';
    } catch (error) {
      console.error('Failed to get access token:', error);
      return '';
    }
  };

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;
    if (!env.API_URL) {
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: 'Konfigurasi EXPO_PUBLIC_API_URL belum diatur. Set juga EXPO_PUBLIC_API_URL_LAN untuk iOS/Android.', timestamp: new Date() }]);
      return;
    }
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    const userInput = inputText.trim();
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch(`${env.API_URL}/api/v1/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Authorization': `Bearer ${await getAccessToken()}`,
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId,
          llm_config: { model: selectedModel, temperature: 0.7 },
        }),
      });
      if (!response.ok) throw new Error('Failed to send message');

      const assistantMsgId = (Date.now() + 1).toString();
      setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '', thinking: undefined, timestamp: new Date() }]);

      const contentType = response.headers.get('content-type') || '';
      const isSSE = contentType.includes('text/event-stream');
      const canStream = !!response.body;

      if (!canStream) {
        const text = await response.text();
        let aggregated = '';
        try {
          const json = JSON.parse(text);
          const extract = (p: any): string => (p?.content ?? p?.delta ?? p?.text ?? p?.message ?? p?.choices?.[0]?.delta?.content ?? '');
          aggregated = extract(json) || String(json);
        } catch { aggregated = text; }
        const { thinking, content } = parseStreamingText(aggregated);
        setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content, thinking } : m));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let aggregated = '';
      let newConversationId = conversationId;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = isSSE ? buffer.split(/\r?\n\r?\n/) : buffer.split(/\r?\n/);
        buffer = chunks.pop() || '';

        for (const rawChunk of chunks) {
          if (!rawChunk) continue;
          if (isSSE) {
            const lines = rawChunk.split(/\r?\n/).filter(Boolean);
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              const data = line.slice(6).trim();
              if (!data || data === '[DONE]') continue;
              processEvent(data);
            }
          } else {
            processEvent(rawChunk);
          }
        }
      }

      function processEvent(jsonLine: string) {
        try {
          const payload = JSON.parse(jsonLine);
          const cid = (payload.conversation_id || payload?.payload?.conversation_id) as string | undefined;
          if (cid && !newConversationId) {
            newConversationId = cid;
            setConversationId(newConversationId);
            // Update URL only (no redirect, no reload)
            if (typeof window !== 'undefined') {
              // For web: update URL to /chat/[conversation_id] only
              const url = `/chat/${newConversationId}`;
              window.history.replaceState(null, '', url);
            } else if (router.setParams) {
              // For native: update params if possible
              router.setParams({ conversation_id: newConversationId });
            }
          }
          if (payload.type === 'final_state') {
            const usagePayload = payload.payload || {};
            const usage: UsageInfo = {
              input_tokens: usagePayload.input_token_count ?? usagePayload.input_tokens,
              output_tokens: usagePayload.output_token_count ?? usagePayload.output_tokens,
              cost: usagePayload.cost_estimate ?? usagePayload.cost,
              model: usagePayload.model_used ?? usagePayload.model,
            };
            setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, usage } : m));
            return;
          }
          const extract = (p: any): string => {
            if (!p) return '';
            if (p.type === 'token_chunk' && typeof p.payload === 'string') return p.payload as string;
            return p?.content ?? p?.delta ?? p?.text ?? p?.message ?? p?.choices?.[0]?.delta?.content ?? '';
          };
          const piece = extract(payload);
          if (piece) {
            aggregated += String(piece);
            const { thinking, content, isThinkingActive } = parseStreamingText(aggregated);
            setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content, thinking } : m));
            if (isThinkingActive) {
              setShowThinking(prev => ({ ...prev, [assistantMsgId]: true }));
            } else if (thinking && !isThinkingActive && content) {
              setShowThinking(prev => ({ ...prev, [assistantMsgId]: false }));
            }
          }
        } catch { /* ignore malformed */ }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: 'Maaf, terjadi kesalahan. Silakan coba lagi.', timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { scrollViewRef.current?.scrollToEnd({ animated: true }); }, [messages]);

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
            {['gemini-2.5-flash','gpt-4o-mini','deepseek-v3','moonshot-v1-32k','grok-4'].map(m => (
              <TouchableOpacity key={m} style={[styles.modelMenuItem, selectedModel === m && styles.modelMenuItemActive]} onPress={() => { setSelectedModel(m); setModelMenuOpen(false); }}>
                <Text style={styles.modelMenuText}>{m}</Text>
                {selectedModel === m && <Ionicons name="checkmark" size={14} color="#10b981" />}
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
      <ScrollView ref={scrollViewRef} style={styles.messagesContainer} contentContainerStyle={styles.messagesContent} showsVerticalScrollIndicator={false}>
        {messages.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={64} color="#71767b" />
            <Text style={styles.emptyTitle}>Mulai Percakapan</Text>
            <Text style={styles.emptySubtitle}>Tanyakan apa saja kepada AI Assistant</Text>
          </View>
        ) : (
          messages.map(message => (
            <View key={message.id} style={[styles.messageBubble, message.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
              <View style={styles.messageHeader}>
                <Ionicons name={message.role === 'user' ? 'person-circle' : 'sparkles'} size={20} color={message.role === 'user' ? '#1d9bf0' : '#10b981'} />
                <Text style={styles.messageRole}>{message.role === 'user' ? user?.name || 'You' : 'AI Assistant'}</Text>
              </View>
              {message.thinking && message.role === 'assistant' && (
                <View style={styles.thinkingContainer}>
                  <TouchableOpacity style={styles.thinkingHeader} onPress={() => toggleThinking(message.id)} activeOpacity={0.7}>
                    <Ionicons name="bulb-outline" size={16} color="#fbbf24" />
                    <Text style={styles.thinkingTitle}>Thinking Process</Text>
                    <Ionicons name={showThinking[message.id] ? 'chevron-up' : 'chevron-down'} size={16} color="#71767b" />
                  </TouchableOpacity>
                  {showThinking[message.id] && (
                    <View style={styles.thinkingContent}>
                      <Text style={styles.thinkingText}>{message.thinking}</Text>
                    </View>
                  )}
                </View>
              )}
              <MarkdownText style={styles.messageContent}>{message.content}</MarkdownText>
              {message.usage && (
                <View style={styles.usageBar}>
                  {message.usage.model && <Text style={styles.usageItem}>Model: {message.usage.model}</Text>}
                  {message.usage.input_tokens !== undefined && <Text style={styles.usageItem}>In: {message.usage.input_tokens}</Text>}
                  {message.usage.output_tokens !== undefined && <Text style={styles.usageItem}>Out: {message.usage.output_tokens}</Text>}
                  {message.usage.cost !== undefined && <Text style={styles.usageItem}>Cost: {message.usage.cost}</Text>}
                </View>
              )}
            </View>
          ))
        )}
        {isLoading && (
          <View style={styles.loadingBubble}>
            <ActivityIndicator size="small" color="#71767b" />
            <Text style={styles.loadingText}>AI sedang mengetik...</Text>
          </View>
        )}
      </ScrollView>
      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="Ketik pesan..." placeholderTextColor="#71767b" value={inputText} onChangeText={setInputText} multiline maxLength={2000} editable={!isLoading} />
        <TouchableOpacity style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]} onPress={handleSend} disabled={!inputText.trim() || isLoading}>
          <Ionicons name="send" size={20} color={inputText.trim() && !isLoading ? '#1d9bf0' : '#71767b'} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

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
  assistantBubble: { alignSelf: 'flex-start', backgroundColor: '#2f3336' },
  messageHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  messageRole: { color: '#fff', fontSize: 13, fontWeight: '600' },
  messageContent: { color: '#fff', fontSize: 15, lineHeight: 20 },
  thinkingContainer: { backgroundColor: 'rgba(251, 191, 36, 0.1)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(251, 191, 36, 0.3)', marginBottom: 12, overflow: 'hidden' },
  thinkingHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10 },
  thinkingTitle: { flex: 1, color: '#fbbf24', fontSize: 13, fontWeight: '600' },
  thinkingContent: { padding: 10, paddingTop: 0 },
  thinkingText: { color: '#d1d5db', fontSize: 13, lineHeight: 18, fontStyle: 'italic' },
  usageBar: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  usageItem: { color: '#71767b', fontSize: 12 },
  loadingBubble: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12, alignSelf: 'flex-start' },
  loadingText: { color: '#71767b', fontSize: 14, fontStyle: 'italic' },
  inputContainer: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, borderTopWidth: 1, borderTopColor: '#2f3336', backgroundColor: '#000', gap: 8 },
  input: { flex: 1, backgroundColor: '#2f3336', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, color: '#fff', fontSize: 15, maxHeight: 100 },
  sendButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#2f3336', justifyContent: 'center', alignItems: 'center' },
  sendButtonDisabled: { opacity: 0.5 },
});