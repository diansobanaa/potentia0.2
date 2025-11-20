 
import { create } from 'zustand';
import { chatApi } from './api';
import type { 
  Conversation, 
  Message, 
  ChatRequest, 
  LLMConfig,
  ToolApprovalRequest,
  StreamMetadata
} from './types';

interface ChatState {
  conversations: Conversation[];
  messages: Record<string, Message[]>;
  activeConversationId: string | null;
  
  streamingMessage: string;
  streamingStatus: string;
  isLoading: boolean;
  
  approvalRequest: ToolApprovalRequest | null;
  currentMetadata: StreamMetadata | null;
  stopStreamFn: (() => void) | null;

  sendMessage: (text: string, llmConfig?: LLMConfig) => Promise<void>;
  approveTool: () => Promise<void>;
  rejectTool: () => Promise<void>;
  stopStream: () => void;
  loadConversations: (page?: number) => Promise<void>;
  loadMessages: (conversationId: string, page?: number) => Promise<void>;
  setActiveConversation: (conversationId: string | null) => void;
  
  // Actions internal
  _appendStreamChunk: (chunk: string) => void;
  _setStreamingStatus: (status: string) => void;
  _setMetadata: (metadata: StreamMetadata) => void;
  _setApprovalRequest: (request: ToolApprovalRequest) => void;
  _clearStreamingState: () => void;
  _addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  messages: {},
  activeConversationId: null,
  streamingMessage: '',
  streamingStatus: '',
  isLoading: false,
  approvalRequest: null,
  currentMetadata: null,
  stopStreamFn: null,

  sendMessage: async (text: string, llmConfig?: LLMConfig) => {
    const { activeConversationId, _addMessage, _appendStreamChunk, _setStreamingStatus, _setMetadata, _setApprovalRequest, _clearStreamingState } = get();
    
    set({ 
      isLoading: true, 
      streamingStatus: 'Thinking...', 
      approvalRequest: null,
      streamingMessage: ''
    });

    // 1. Optimistic User Message
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId || 'temp',
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    _addMessage(tempUserMessage);

    try {
      const payload: ChatRequest = {
        message: text,
        conversation_id: activeConversationId || undefined,
        llm_config: llmConfig,
      };

      // 2. Start Stream
      const stopFn = await chatApi.streamChat(payload, {
        onMetadata: (metadata) => {
          _setMetadata(metadata);
          if (!get().activeConversationId) {
            set({ activeConversationId: metadata.conversation_id });
          }
        },
        onStatus: (status) => _setStreamingStatus(status),
        onChunk: (chunk) => _appendStreamChunk(chunk),
        onApproval: (request) => _setApprovalRequest(request),
        onError: (errorMsg) => {
          _setStreamingStatus(`Error: ${errorMsg}`);
          set({ isLoading: false });
        },
        onComplete: (finalState) => {
          const completedMessage: Message = {
            ...finalState.message,
            content: get().streamingMessage,
            conversation_id: get().activeConversationId || ''
          };
          _addMessage(completedMessage);
          _clearStreamingState();
        },
      });

      set({ stopStreamFn: stopFn });

    } catch (error: any) {
      console.error('Send message failed:', error);
      _setStreamingStatus(`Error: ${error.message}`);
      set({ isLoading: false });
    }
  },

  approveTool: async () => {
    const { activeConversationId } = get();
    if (!activeConversationId) return;
    set({ isLoading: true, approvalRequest: null, streamingStatus: 'Executing tool...' });
    try {
      await chatApi.approveTool(activeConversationId);
      set({ isLoading: false, streamingStatus: 'Tool approved.' });
    } catch (error: any) {
      set({ isLoading: false, streamingStatus: `Error: ${error.message}` });
    }
  },

  rejectTool: async () => {
    const { activeConversationId } = get();
    if (!activeConversationId) return;
    set({ isLoading: true, approvalRequest: null, streamingStatus: 'Tool rejected' });
    try {
      await chatApi.rejectTool(activeConversationId);
      set({ isLoading: false });
      get()._clearStreamingState();
    } catch (error: any) {
      set({ isLoading: false, streamingStatus: `Error: ${error.message}` });
    }
  },

  stopStream: () => {
    const { stopStreamFn } = get();
    if (stopStreamFn) {
      stopStreamFn();
      set({ stopStreamFn: null });
    }
    get()._clearStreamingState();
  },

  loadConversations: async (page = 1) => {
    try {
      const response = await chatApi.listConversations(page);
      set({ conversations: response.items });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  },

  loadMessages: async (conversationId: string, page = 1) => {
    try {
      if (page === 1) {
        set((state) => ({ messages: { ...state.messages, [conversationId]: [] } }));
      }
      const response = await chatApi.getMessages(conversationId, page);
      // Map response backend ke format Message store
      const newMessages = response.items.map((m: any) => ({
        id: m.message_id || m.id,
        conversation_id: conversationId,
        role: m.role,
        content: m.content,
        created_at: m.created_at
      })).reverse();

      set((state) => ({
        messages: {
          ...state.messages,
          [conversationId]: page === 1 
            ? newMessages 
            : [...newMessages, ...(state.messages[conversationId] || [])],
        },
      }));
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  },

  setActiveConversation: (conversationId: string | null) => {
    set({ activeConversationId: conversationId });
  },

  _appendStreamChunk: (chunk) => {
    set((state) => ({
      streamingMessage: state.streamingMessage + chunk,
      isLoading: false, // Chunk masuk = loading selesai
    }));
  },
  
  _setStreamingStatus: (status) => set({ streamingStatus: status }),
  _setMetadata: (metadata) => set({ currentMetadata: metadata }),
  _setApprovalRequest: (request) => set({ isLoading: false, approvalRequest: request, streamingStatus: 'Waiting approval...' }),
  
  _clearStreamingState: () => {
    set({
      streamingMessage: '',
      streamingStatus: '',
      isLoading: false,
      approvalRequest: null,
      currentMetadata: null,
      stopStreamFn: null,
    });
  },
  
  _addMessage: (message) => {
    set((state) => {
      const conversationId = message.conversation_id || state.activeConversationId;
      if (!conversationId) return state;
      const currentMessages = state.messages[conversationId] || [];
      return {
        messages: {
          ...state.messages,
          [conversationId]: [...currentMessages, message],
        },
      };
    });
  },
}));