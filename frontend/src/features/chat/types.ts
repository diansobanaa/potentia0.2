// File: src/features/chat/types.ts
import type { components } from "@/src/shared/api/schema";

export type ChatRequest = components["schemas"]["ChatRequest"];

export interface Conversation {
  conversation_id: string;
  title: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
  isStreaming?: boolean; // Penanda visual
  approvalRequest?: ToolApprovalRequest;
}

export interface ToolApprovalRequest {
  tool_name: string;
  tool_args: any;
  thread_id?: string;
  run_id?: string;
  call_id?: string;
}

export interface StreamMetadata {
  conversation_id: string;
  title?: string;
}

export interface LLMConfig {
  model: string;
  temperature?: number;
}

export interface StreamCallbacks {
  onMetadata?: (meta: StreamMetadata) => void;
  onStatus?: (status: string) => void;
  onChunk?: (chunk: string) => void;
  onApproval?: (request: ToolApprovalRequest) => void;
  onError?: (msg: string) => void;
  onComplete?: (finalState: { message: Message }) => void;
}