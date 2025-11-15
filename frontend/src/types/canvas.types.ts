// src/types/canvas.types.ts
import type { User } from './auth.types';

export interface Block {
  id: string;
  canvas_id: string;
  parent_id: string | null;
  type: 'text' | 'heading' | 'list' | 'image' | 'code' | 'shape';
  content: Record<string, any>;
  position: {
    x: number;
    y: number;
  };
  size: {
    width: number;
    height: number;
  };
  y_order: string; // LexoRank
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface Canvas {
  id: string;
  title: string;
  owner_id: string;
  workspace_id: string | null;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CanvasPresence {
  user_id: string;
  user_name: string;
  cursor?: {
    x: number;
    y: number;
  };
  selection?: {
    block_id: string;
  };
  status: 'active' | 'idle' | 'offline';
  color: string;
}

export interface BlockMutation {
  client_op_id: string;
  action: 'create' | 'update' | 'delete' | 'move';
  block_id?: string;
  expected_version?: number;
  update_data?: {
    parent_id?: string;
    type?: Block['type'];
    content?: Record<string, any>;
    position?: Block['position'];
    size?: Block['size'];
    y_order?: string;
  };
}

export interface CanvasState {
  canvas_id: string | null;
  blocks: Record<string, Block>;
  server_seq: number;
  presence: Record<string, CanvasPresence>;
  viewport: {
    x: number;
    y: number;
    zoom: number;
  };
  selectedBlocks: Set<string>;
}

// WebSocket message types from backend
export interface WSMessage {
  type: 'initial_state' | 'mutation' | 'presence' | 'error' | 'ack';
  payload: any;
}

export interface InitialStatePayload {
  blocks: Block[];
  server_seq: number;
}

export interface MutationPayload {
  action: string;
  block_id: string;
  block: Block | null;
  server_seq: number;
  client_op_id: string;
}

export interface PresencePayload {
  user_id: string;
  data: Partial<CanvasPresence>;
}
