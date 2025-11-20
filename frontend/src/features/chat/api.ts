import { env } from '@/src/shared/config/env';
import { supabase } from '@/src/shared/api/supabase';
import type { ChatRequest, StreamCallbacks } from './types';

// --- Helper Throttling ---
// Membatasi update ke UI max 20fps (50ms) agar tidak freeze saat stream cepat
const createThrottledEmitter = (callback: (chunk: string) => void, delay = 50) => {
  let buffer = "";
  let lastEmit = 0;
  let timer: NodeJS.Timeout | null = null;

  return {
    push: (chunk: string) => {
      buffer += chunk;
      const now = Date.now();
      if (now - lastEmit > delay) {
        callback(buffer);
        buffer = "";
        lastEmit = now;
      } else if (!timer) {
        timer = setTimeout(() => {
          if (buffer) {
            callback(buffer);
            buffer = "";
            lastEmit = Date.now();
          }
          timer = null;
        }, delay);
      }
    },
    flush: () => {
      if (timer) clearTimeout(timer);
      if (buffer) callback(buffer);
      buffer = "";
    }
  };
};

// --- Helper Handler Data ---
const handleStreamData = (data: any, chunkEmitter: any, callbacks: StreamCallbacks) => {
  switch (data.type) {
    case 'token_chunk':
      chunkEmitter.push(data.payload);
      break;
    case 'metadata':
      callbacks.onMetadata?.(data.payload);
      break;
    case 'status':
      callbacks.onStatus?.(data.payload);
      break;
    case 'interrupt':
      chunkEmitter.flush(); // Pastikan teks tampil sebelum pause
      callbacks.onApproval?.(data.payload);
      break;
    case 'final_state':
      callbacks.onComplete?.({
        message: {
          id: Date.now().toString(),
          role: 'assistant',
          content: '', 
          created_at: new Date().toISOString()
        }
      });
      break;
    case 'error':
      callbacks.onError?.(data.payload);
      break;
  }
};

export const chatApi = {
  // Menggunakan XMLHttpRequest (XHR) karena fetch stream belum stabil di semua versi RN
  streamChat: async (payload: ChatRequest, callbacks: StreamCallbacks): Promise<() => void> => {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    // Throttler untuk onChunk
    const chunkEmitter = createThrottledEmitter((chunk) => {
      callbacks.onChunk?.(chunk);
    }, 50);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      let lastIndex = 0;
      let buffer = ''; // Penampung potongan JSON yang terpotong di tengah

      xhr.open('POST', `${env.API_URL}/api/v1/chat/`);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('Accept', 'application/x-ndjson');
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      // Event Listener: Dipanggil berulang kali saat data masuk
      xhr.onprogress = () => {
        const currIndex = xhr.responseText.length;
        if (currIndex === lastIndex) return;

        // Ambil hanya potongan data baru
        const newChunk = xhr.responseText.substring(lastIndex, currIndex);
        lastIndex = currIndex;

        // Gabungkan dengan sisa buffer sebelumnya (jika ada)
        const rawData = buffer + newChunk;
        const lines = rawData.split('\n');

        // Simpan baris terakhir (mungkin belum lengkap) kembali ke buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const data = JSON.parse(trimmed);
            handleStreamData(data, chunkEmitter, callbacks);
          } catch (e) {
            // JSON Parse error wajar terjadi jika paket terpotong, tunggu chunk berikutnya
          }
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          // Proses sisa buffer terakhir jika ada
          if (buffer.trim()) {
            try {
              const data = JSON.parse(buffer.trim());
              handleStreamData(data, chunkEmitter, callbacks);
            } catch (e) {}
          }
          chunkEmitter.flush();
        } else {
          // Coba parse error message dari backend jika ada
          let errorMsg = `HTTP Error ${xhr.status}`;
          try {
             const errJson = JSON.parse(xhr.responseText);
             if (errJson.detail) errorMsg = errJson.detail;
          } catch (e) {}
          callbacks.onError?.(errorMsg);
        }
      };

      xhr.onerror = () => {
        callbacks.onError?.('Network request failed');
      };

      xhr.send(JSON.stringify(payload));

      // Resolve dengan fungsi abort yang bisa dipanggil store
      resolve(() => {
        xhr.abort();
      });
    });
  },

  // --- Endpoint Lain (Standar Fetch) ---
  listConversations: async (page = 1) => {
    const { data: { session } } = await supabase.auth.getSession();
    const res = await fetch(`${env.API_URL}/api/v1/chat/conversations-list?page=${page}&size=20`, {
      headers: { 'Authorization': `Bearer ${session?.access_token}` }
    });
    return res.json();
  },

  getMessages: async (conversationId: string, page = 1) => {
    const { data: { session } } = await supabase.auth.getSession();
    const res = await fetch(`${env.API_URL}/api/v1/chat/${conversationId}/messages?page=${page}&size=50`, {
      headers: { 'Authorization': `Bearer ${session?.access_token}` }
    });
    return res.json();
  },

  approveTool: async (conversationId: string) => {
    // Placeholder: Sesuaikan dengan endpoint resume/approve backend Anda
    console.log("Approving tool:", conversationId);
  },

  rejectTool: async (conversationId: string) => {
    // Placeholder: Sesuaikan dengan endpoint reject backend Anda
    console.log("Rejecting tool:", conversationId);
  }
};