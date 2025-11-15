// src/features/canvas/store/canvasStore.ts
import { create } from 'zustand';
import { canvasWebSocket } from '@services/canvas/CanvasWebSocket';
import { canvasApi } from '@services/api/canvas.api';
import type {
  Block,
  Canvas,
  CanvasPresence,
  BlockMutation,
  InitialStatePayload,
  MutationPayload,
  PresencePayload,
} from '../../../types/canvas.types';

interface CanvasStore {
  // State
  canvas: Canvas | null;
  blocks: Record<string, Block>;
  serverSeq: number;
  presence: Record<string, CanvasPresence>;
  viewport: {
    x: number;
    y: number;
    zoom: number;
  };
  selectedBlocks: Set<string>;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  connectToCanvas: (canvasId: string) => Promise<void>;
  disconnectFromCanvas: () => void;
  createBlock: (type: Block['type'], position: { x: number; y: number }) => void;
  updateBlock: (blockId: string, updates: Partial<Block>) => void;
  deleteBlock: (blockId: string) => void;
  moveBlock: (blockId: string, position: { x: number; y: number }) => void;
  selectBlock: (blockId: string, multi?: boolean) => void;
  clearSelection: () => void;
  updateViewport: (viewport: Partial<CanvasStore['viewport']>) => void;
  updateCursor: (cursor: { x: number; y: number }) => void;
  
  // Internal
  _handleInitialState: (payload: InitialStatePayload) => void;
  _handleMutation: (payload: MutationPayload) => void;
  _handlePresence: (payload: PresencePayload) => void;
  _setError: (error: string) => void;
  _setConnected: (connected: boolean) => void;
}

const generateClientOpId = () => `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const useCanvasStore = create<CanvasStore>((set, get) => ({
  // Initial state
  canvas: null,
  blocks: {},
  serverSeq: 0,
  presence: {},
  viewport: { x: 0, y: 0, zoom: 1 },
  selectedBlocks: new Set(),
  isConnected: false,
  isLoading: false,
  error: null,

  // Connect to canvas
  connectToCanvas: async (canvasId: string) => {
    set({ isLoading: true, error: null });

    try {
      // Fetch canvas metadata
      const canvas = await canvasApi.getCanvas(canvasId);
      set({ canvas });

      // Connect WebSocket
      await canvasWebSocket.connect(canvasId, {
        onInitialState: (payload) => get()._handleInitialState(payload),
        onMutation: (payload) => get()._handleMutation(payload),
        onPresence: (payload) => get()._handlePresence(payload),
        onError: (message) => get()._setError(message),
        onClose: () => get()._setConnected(false),
      });

      set({ isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to connect', isLoading: false });
    }
  },

  // Disconnect from canvas
  disconnectFromCanvas: () => {
    const { canvas } = get();
    if (canvas) {
      canvasWebSocket.disconnect();
      canvasApi.leaveCanvas(canvas.id).catch(console.error);
    }
    set({
      canvas: null,
      blocks: {},
      serverSeq: 0,
      presence: {},
      isConnected: false,
      selectedBlocks: new Set(),
    });
  },

  // Create block
  createBlock: (type, position) => {
    const { canvas } = get();
    if (!canvas) return;

    const mutation: BlockMutation = {
      client_op_id: generateClientOpId(),
      action: 'create',
      update_data: {
        type,
        content: {},
        position,
        size: { width: 200, height: 100 },
        parent_id: null,
      },
    };

    canvasWebSocket.sendMutation(mutation);
  },

  // Update block
  updateBlock: (blockId, updates) => {
    const { blocks } = get();
    const block = blocks[blockId];
    if (!block) return;

    const mutation: BlockMutation = {
      client_op_id: generateClientOpId(),
      action: 'update',
      block_id: blockId,
      expected_version: block.version,
      update_data: updates,
    };

    canvasWebSocket.sendMutation(mutation);
  },

  // Delete block
  deleteBlock: (blockId) => {
    const { blocks } = get();
    const block = blocks[blockId];
    if (!block) return;

    const mutation: BlockMutation = {
      client_op_id: generateClientOpId(),
      action: 'delete',
      block_id: blockId,
      expected_version: block.version,
    };

    canvasWebSocket.sendMutation(mutation);
  },

  // Move block
  moveBlock: (blockId, position) => {
    get().updateBlock(blockId, { position });
  },

  // Select block
  selectBlock: (blockId, multi = false) => {
    set((state) => {
      const newSelection = new Set(multi ? state.selectedBlocks : []);
      if (newSelection.has(blockId)) {
        newSelection.delete(blockId);
      } else {
        newSelection.add(blockId);
      }
      return { selectedBlocks: newSelection };
    });
  },

  // Clear selection
  clearSelection: () => {
    set({ selectedBlocks: new Set() });
  },

  // Update viewport (pan/zoom)
  updateViewport: (viewportUpdate) => {
    set((state) => ({
      viewport: { ...state.viewport, ...viewportUpdate },
    }));
  },

  // Update cursor position (sends presence)
  updateCursor: (cursor) => {
    canvasWebSocket.sendPresence({ cursor });
  },

  // Internal: Handle initial state from WebSocket
  _handleInitialState: (payload) => {
    const blocksMap: Record<string, Block> = {};
    payload.blocks.forEach((block: Block) => {
      blocksMap[block.id] = block;
    });

    set({
      blocks: blocksMap,
      serverSeq: payload.server_seq,
      isConnected: true,
      isLoading: false,
    });
  },

  // Internal: Handle mutation from WebSocket
  _handleMutation: (payload) => {
    set((state) => {
      const newBlocks = { ...state.blocks };

      if (payload.action === 'delete') {
        delete newBlocks[payload.block_id];
      } else if (payload.block) {
        newBlocks[payload.block_id] = payload.block;
      }

      return {
        blocks: newBlocks,
        serverSeq: payload.server_seq,
      };
    });
  },

  // Internal: Handle presence update from WebSocket
  _handlePresence: (payload) => {
    set((state) => ({
      presence: {
        ...state.presence,
        [payload.user_id]: {
          ...state.presence[payload.user_id],
          ...payload.data,
          user_id: payload.user_id,
        },
      },
    }));
  },

  // Internal: Set error
  _setError: (error) => {
    set({ error, isLoading: false });
  },

  // Internal: Set connected
  _setConnected: (connected) => {
    set({ isConnected: connected });
  },
}));
