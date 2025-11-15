// src/services/api/chat.api.ts
import { EventSourcePolyfill } from 'event-source-polyfill';
import apiClient from './client';
import { getToken } from '@services/storage/SecureStorage';
import { ENV } from '@config/env';
import type { 
  ChatRequest, 
  Conversation, 
  Message,
  ToolApprovalRequest,
  StreamMetadata,
  FinalState
} from '@types/chat.types';
import type { PaginatedResponse } from '@types/api.types';

interface StreamCallbacks {
  onMetadata: (data: StreamMetadata) => void;
  onStatus: (status: string) => void;
  onChunk: (chunk: string) => void;
  onApproval: (request: ToolApprovalRequest) => void;
  onError: (errorMsg: string) => void;
  onComplete: (finalState: FinalState) => void;
}

export const chatApi = {
  /**
   * Get paginated list of conversations
   */
  listConversations: async (page: number = 1, size: number = 20): Promise<PaginatedResponse<Conversation>> => {
    const response = await apiClient.get('/api/v1/chat/conversations-list', {
      params: { page, size },
    });
    return response.data;
  },

  /**
   * Get messages for a conversation
   */
  getMessages: async (
    conversationId: string, 
    page: number = 1, 
    size: number = 50
  ): Promise<PaginatedResponse<Message>> => {
    const response = await apiClient.get(`/api/v1/chat/${conversationId}/messages`, {
      params: { page, size },
    });
    return response.data;
  },

  /**
   * Get list of available models
   */
  getAvailableModels: async (): Promise<{ available_models: string[]; total_count: number }> => {
    const response = await apiClient.get('/api/v1/chat/models/available');
    return response.data;
  },

  /**
   * Approve tool execution (Human-in-the-Loop)
   */
  approveTool: async (conversationId: string): Promise<void> => {
    await apiClient.post(`/api/v1/chat/${conversationId}/actions/approve_tool`);
  },

  /**
   * Reject tool execution (Human-in-the-Loop)
   */
  rejectTool: async (conversationId: string): Promise<void> => {
    await apiClient.post(`/api/v1/chat/${conversationId}/actions/reject_tool`);
  },

  /**
   * Stream chat with Server-Sent Events
   * Replaces ChatStreamService.ts - more declarative with callbacks
   */
  streamChat: async (payload: ChatRequest, callbacks: StreamCallbacks): Promise<() => void> => {
    const token = await getToken();
    
    if (!token) {
      callbacks.onError('No authentication token');
      return () => {};
    }

    const eventSource = new EventSourcePolyfill(
      `${ENV.API_BASE_URL}/api/v1/chat/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      }
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'metadata':
            callbacks.onMetadata(data.payload);
            break;
          
          case 'status':
            callbacks.onStatus(data.payload);
            break;
          
          case 'token_chunk':
            callbacks.onChunk(data.payload);
            break;
          
          case 'tool_approval_required':
            // CRITICAL: Human-in-the-Loop
            callbacks.onApproval(data.payload);
            eventSource.close();
            break;
          
          case 'final_state':
            callbacks.onComplete(data.payload);
            eventSource.close();
            break;
          
          case 'errorStatus':
            callbacks.onError(data.payload);
            break;
          
          case 'error':
            callbacks.onError(data.detail || 'Stream error');
            eventSource.close();
            break;
        }
      } catch (parseError) {
        console.error('Failed to parse SSE event:', parseError);
        callbacks.onError('Failed to parse server response');
      }
    };
    
    eventSource.onerror = (err) => {
      console.error('EventSource failed:', err);
      callbacks.onError('Connection error');
      eventSource.close();
    };

    // Return cleanup function
    return () => {
      eventSource.close();
    };
  },
};
