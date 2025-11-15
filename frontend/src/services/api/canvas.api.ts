// src/services/api/canvas.api.ts
import apiClient from './client';
import { ENV } from '@config/env';
import type { Canvas, Block } from '../../types/canvas.types';
import type { PaginatedResponse } from '../../types/api.types';

export const canvasApi = {
  /**
   * List user's canvases (A4)
   */
  listCanvases: async (page: number = 1, size: number = 20): Promise<PaginatedResponse<Canvas>> => {
    const response = await apiClient.get('/api/v1/canvas', {
      params: { page, size },
    });
    return response.data;
  },

  /**
   * Create new canvas (A5)
   */
  createCanvas: async (title: string, workspaceId?: string): Promise<Canvas> => {
    const response = await apiClient.post('/api/v1/canvas', {
      title,
      workspace_id: workspaceId || null,
    });
    return response.data;
  },

  /**
   * Get canvas detail (A1)
   */
  getCanvas: async (canvasId: string): Promise<Canvas> => {
    const response = await apiClient.get(`/api/v1/canvas/${canvasId}`);
    return response.data;
  },

  /**
   * Get canvas blocks paginated (A2)
   */
  getBlocks: async (
    canvasId: string,
    page: number = 1,
    size: number = 100
  ): Promise<PaginatedResponse<Block>> => {
    const response = await apiClient.get(`/api/v1/canvas/${canvasId}/blocks`, {
      params: { page, size },
    });
    return response.data;
  },

  /**
   * Get single block (A3)
   */
  getBlock: async (canvasId: string, blockId: string): Promise<Block> => {
    const response = await apiClient.get(`/api/v1/canvas/${canvasId}/blocks/${blockId}`);
    return response.data;
  },

  /**
   * Update canvas settings (A6)
   */
  updateCanvas: async (
    canvasId: string,
    updates: { title?: string; settings?: Record<string, any> }
  ): Promise<Canvas> => {
    const response = await apiClient.patch(`/api/v1/canvas/${canvasId}`, updates);
    return response.data;
  },

  /**
   * Delete canvas (A7)
   */
  deleteCanvas: async (canvasId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/canvas/${canvasId}`);
  },

  /**
   * HTTP Fallback: Mutate block (H2)
   */
  mutateBlock: async (canvasId: string, mutation: any): Promise<any> => {
    const response = await apiClient.post(`/api/v1/canvas/${canvasId}/mutate`, mutation);
    return response.data;
  },

  /**
   * HTTP Fallback: Update presence (H3)
   */
  updatePresence: async (canvasId: string, presence: any): Promise<void> => {
    await apiClient.post(`/api/v1/canvas/${canvasId}/presence`, presence);
  },

  /**
   * Leave canvas (H6)
   */
  leaveCanvas: async (canvasId: string): Promise<void> => {
    await apiClient.post(`/api/v1/canvas/${canvasId}/leave`);
  },
};
