// src/types/chat.types.ts
export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: {
    model?: string;
    tokens?: { 
      input: number; 
      output: number; 
    };
  };
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
  llm_config?: LLMConfig;
}

export interface LLMConfig {
  model: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ToolApprovalRequest {
  tool_name: string;
  args: Record<string, any>;
  reasoning?: string;
  conversation_id: string;
}

export interface StreamMetadata {
  conversation_id: string;
  message_id: string;
  model: string;
}

export interface FinalState {
  message: Message;
  tokens: {
    input: number;
    output: number;
  };
}
