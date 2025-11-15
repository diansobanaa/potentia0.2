// src/features/chat/store/chatStore.ts
import { create } from 'zustand';
import { chatApi } from '@services/api/chat.api';
import type { 
  Conversation, 
  Message, 
  ChatRequest, 
  LLMConfig,
  ToolApprovalRequest,
  StreamMetadata,
  FinalState
} from '@types/chat.types';

interface ChatState {
  // Data state
  conversations: Conversation[];
  messages: Record<string, Message[]>;
  activeConversationId: string | null;
  
  // Streaming state
  streamingMessage: string;
  streamingStatus: string;
  isLoading: boolean;
  
  // Human-in-the-Loop state
  approvalRequest: ToolApprovalRequest | null;
  
  // Metadata
  currentMetadata: StreamMetadata | null;
  
  // Cleanup
  stopStreamFn: (() => void) | null;

  // Public actions
  sendMessage: (text: string, llmConfig?: LLMConfig) => Promise<void>;
  approveTool: () => Promise<void>;
  rejectTool: () => Promise<void>;
  stopStream: () => void;
  loadConversations: (page?: number) => Promise<void>;
  loadMessages: (conversationId: string, page?: number) => Promise<void>;
  setActiveConversation: (conversationId: string | null) => void;
  
  // Internal actions (called by API callbacks)
  _appendStreamChunk: (chunk: string) => void;
  _setStreamingStatus: (status: string) => void;
  _setMetadata: (metadata: StreamMetadata) => void;
  _setApprovalRequest: (request: ToolApprovalRequest) => void;
  _clearStreamingState: () => void;
  _addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  conversations: [],
  messages: {},
  activeConversationId: null,
  streamingMessage: '',
  streamingStatus: '',
  isLoading: false,
  approvalRequest: null,
  currentMetadata: null,
  stopStreamFn: null,

  // Send message with streaming
  sendMessage: async (text: string, llmConfig?: LLMConfig) => {
    const { activeConversationId, _addMessage, _appendStreamChunk, _setStreamingStatus, _setMetadata, _setApprovalRequest, _clearStreamingState } = get();
    
    set({ 
      isLoading: true, 
      streamingStatus: 'Sending...', 
      approvalRequest: null,
      streamingMessage: ''
    });

    // Optimistically add user message to UI
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId || '',
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    _addMessage(tempUserMessage);

    try {
      const payload: ChatRequest = {
        message: text,
        conversation_id: activeConversationId,
        llm_config: llmConfig,
      };

      // Start SSE stream
      const stopFn = await chatApi.streamChat(payload, {
        onMetadata: (metadata) => {
          _setMetadata(metadata);
          // Update active conversation if new
          if (!activeConversationId) {
            set({ activeConversationId: metadata.conversation_id });
          }
        },
        
        onStatus: (status) => {
          _setStreamingStatus(status);
        },
        
        onChunk: (chunk) => {
          _appendStreamChunk(chunk);
        },
        
        onApproval: (request) => {
          // Human-in-the-Loop: pause and wait for user approval
          _setApprovalRequest(request);
        },
        
        onError: (errorMsg) => {
          _setStreamingStatus(`Error: ${errorMsg}`);
          setTimeout(() => _clearStreamingState(), 3000);
        },
        
        onComplete: (finalState) => {
          // Move streaming message to messages list
          _addMessage(finalState.message);
          _clearStreamingState();
        },
      });

      set({ stopStreamFn: stopFn });

    } catch (error: any) {
      console.error('Send message failed:', error);
      _setStreamingStatus(`Error: ${error.message}`);
      setTimeout(() => _clearStreamingState(), 3000);
    }
  },

  // Approve tool execution (HiTL)
  approveTool: async () => {
    const { activeConversationId, approvalRequest } = get();
    
    if (!activeConversationId) {
      console.error('No active conversation');
      return;
    }

    set({ 
      isLoading: true, 
      approvalRequest: null, 
      streamingStatus: 'Executing tool...' 
    });

    try {
      await chatApi.approveTool(activeConversationId);
      
      // Note: Backend will continue stream, but we don't implement
      // "resume" stream here for simplicity. User can refresh messages.
      set({ 
        isLoading: false,
        streamingStatus: 'Tool approved. Refresh to see results.'
      });
      
      setTimeout(() => {
        get()._clearStreamingState();
      }, 3000);

    } catch (error: any) {
      console.error('Tool approval failed:', error);
      set({ 
        isLoading: false,
        streamingStatus: `Error: ${error.message}`
      });
    }
  },

  // Reject tool execution (HiTL)
  rejectTool: async () => {
    const { activeConversationId } = get();
    
    if (!activeConversationId) {
      console.error('No active conversation');
      return;
    }

    set({ 
      isLoading: true, 
      approvalRequest: null, 
      streamingStatus: 'Tool rejected' 
    });

    try {
      await chatApi.rejectTool(activeConversationId);
      
      set({ isLoading: false });
      setTimeout(() => {
        get()._clearStreamingState();
      }, 2000);

    } catch (error: any) {
      console.error('Tool rejection failed:', error);
      set({ 
        isLoading: false,
        streamingStatus: `Error: ${error.message}`
      });
    }
  },

  // Stop streaming manually
  stopStream: () => {
    const { stopStreamFn } = get();
    if (stopStreamFn) {
      stopStreamFn();
      set({ stopStreamFn: null });
    }
    get()._clearStreamingState();
  },

  // Load conversations list
  loadConversations: async (page = 1) => {
    try {
      const response = await chatApi.listConversations(page);
      set({ conversations: response.items });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  },

  // Load messages for a conversation
  loadMessages: async (conversationId: string, page = 1) => {
    try {
      const response = await chatApi.getMessages(conversationId, page);
      set((state) => ({
        messages: {
          ...state.messages,
          [conversationId]: response.items,
        },
      }));
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  },

  // Set active conversation
  setActiveConversation: (conversationId: string | null) => {
    set({ activeConversationId: conversationId });
  },

  // Internal actions
  _appendStreamChunk: (chunk) => {
    set((state) => ({
      streamingMessage: state.streamingMessage + chunk,
      isLoading: false, // First chunk means loading is done
    }));
  },
  
  _setStreamingStatus: (status) => {
    set({ streamingStatus: status });
  },
  
  _setMetadata: (metadata) => {
    set({ currentMetadata: metadata });
  },
  
  _setApprovalRequest: (request) => {
    set({ 
      isLoading: false,
      approvalRequest: request,
      streamingStatus: 'Waiting for approval...'
    });
  },

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
      const conversationId = message.conversation_id;
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
