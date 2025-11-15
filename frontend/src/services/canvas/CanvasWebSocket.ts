// src/services/canvas/CanvasWebSocket.ts
import { getToken } from '@services/storage/SecureStorage';
import { ENV } from '@config/env';
import type { WSMessage, BlockMutation, CanvasPresence } from '../../types/canvas.types';

interface CanvasWSCallbacks {
  onInitialState: (payload: any) => void;
  onMutation: (payload: any) => void;
  onPresence: (payload: any) => void;
  onError: (message: string) => void;
  onClose: () => void;
}

export class CanvasWebSocketService {
  private ws: WebSocket | null = null;
  private canvasId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private callbacks: CanvasWSCallbacks | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  async connect(canvasId: string, callbacks: CanvasWSCallbacks): Promise<void> {
    this.canvasId = canvasId;
    this.callbacks = callbacks;

    const token = await getToken();
    if (!token) {
      callbacks.onError('No authentication token');
      return;
    }

    const wsUrl = ENV.WS_BASE_URL.replace('http', 'ws');
    const url = `${wsUrl}/ws/canvas/${canvasId}?token=${token}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('Canvas WebSocket connected');
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('Canvas WebSocket error:', error);
        callbacks.onError('Connection error');
      };

      this.ws.onclose = () => {
        console.log('Canvas WebSocket closed');
        this.stopHeartbeat();
        callbacks.onClose();
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Failed to connect Canvas WebSocket:', error);
      callbacks.onError('Failed to connect');
    }
  }

  private handleMessage(message: WSMessage): void {
    if (!this.callbacks) return;

    switch (message.type) {
      case 'initial_state':
        this.callbacks.onInitialState(message.payload);
        break;
      case 'mutation':
        this.callbacks.onMutation(message.payload);
        break;
      case 'presence':
        this.callbacks.onPresence(message.payload);
        break;
      case 'error':
        this.callbacks.onError(message.payload?.message || 'Unknown error');
        break;
      case 'ack':
        // Acknowledgment - can be used for optimistic UI confirmation
        break;
    }
  }

  sendMutation(mutation: BlockMutation): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, mutation not sent');
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: 'mutation',
        payload: mutation,
      })
    );
  }

  sendPresence(presence: Partial<CanvasPresence>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: 'presence',
        payload: presence,
      })
    );
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Every 30s
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      if (this.canvasId && this.callbacks) {
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        this.connect(this.canvasId, this.callbacks);
      }
    }, delay);
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.canvasId = null;
    this.callbacks = null;
    this.reconnectAttempts = 0;
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
export const canvasWebSocket = new CanvasWebSocketService();
