// src/features/chat/hooks/useChatStream.ts

import { useRef, useState, useCallback } from "react";
import type { components } from "@/src/shared/api/schema";

export type ChatRequest = components["schemas"]["ChatRequest"];

type StreamChunk = {
  type: "token_chunk" | "status" | "metadata" | "final_state" | "interrupt" | "tool_start" | "tool_end" | "error" | string;
  payload: any;
};

interface UseChatStreamOptions {
  apiUrl: string;
  accessToken: string;
  onToken?: (token: string) => void;
  onStatus?: (status: string) => void; // Backend mengirim "Thinking..."
  onMetadata?: (meta: any) => void;
  onFinal?: (final: any) => void;
  onInterrupt?: (payload: any) => void;
  onToolStart?: (payload: { tool: string; input: any }) => void;
  onToolEnd?: (payload: { tool: string; output: any }) => void;
  onChunk?: (chunk: StreamChunk) => void;
  onDone?: (finalData?: any) => void;
  onError?: (error: Error) => void;
}

interface UseChatStreamResult {
  sendMessage: (body: ChatRequest) => void;
  cancel: () => void;
  loading: boolean;    // Koneksi terbuka
  isThinking: boolean; // AI sedang memproses, belum ada token
  error: Error | null;
}

export function useChatStream({
  apiUrl,
  accessToken,
  onToken,
  onStatus,
  onMetadata,
  onFinal,
  onInterrupt,
  onToolStart,
  onToolEnd,
  onChunk,
  onDone,
  onError,
}: UseChatStreamOptions): UseChatStreamResult {
  const controllerRef = useRef<AbortController | null>(null);
  const [loading, setLoading] = useState(false);
  const [isThinking, setIsThinking] = useState(false); // State baru
  const [error, setError] = useState<Error | null>(null);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    setLoading(false);
    setIsThinking(false);
  }, []);

  const sendMessage = useCallback(
    (body: ChatRequest) => {
      setLoading(true);
      setIsThinking(true); // Mulai thinking saat request dikirim
      setError(null);
      
      const controller = new AbortController();
      controllerRef.current = controller;

      fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/x-ndjson",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
        .then(async (res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          
          const reader = res.body?.getReader();
          
          const processLine = (line: string) => {
            const trimmed = line.trim();
            if (!trimmed) return;
            try {
              const obj: StreamChunk = JSON.parse(trimmed);
              
              // Jika terima token atau interrupt, berarti sudah tidak thinking
              if (obj.type === "token_chunk" || obj.type === "interrupt" || obj.type === "final_state") {
                setIsThinking(false);
              }

              switch (obj.type) {
                case "token_chunk":
                  onToken?.(obj.payload);
                  break;
                case "status":
                  // Status update (misal: "Searching google...") tetap dianggap thinking/processing
                  onStatus?.(obj.payload);
                  break;
                case "tool_start":
                  setIsThinking(true); // Masuk mode thinking lagi saat pakai tool
                  onToolStart?.(obj.payload);
                  break;
                case "tool_end":
                  // Jangan matikan thinking di sini, tunggu token hasil tool keluar
                  onToolEnd?.(obj.payload);
                  break;
                case "interrupt":
                  onInterrupt?.(obj.payload);
                  break;
                case "metadata":
                  onMetadata?.(obj.payload);
                  break;
                case "final_state":
                  onFinal?.(obj.payload);
                  break;
                case "error":
                   if(onError) onError(new Error(obj.payload));
                   break;
              }
              onChunk?.(obj);
              
              if (obj.type === 'end') {
                 onDone?.(obj.payload);
              }

            } catch (e) {
              console.warn('[STREAM PARSE ERROR]', trimmed, e);
            }
          };

          if (!reader) {
            // Fallback Text Mode
            const text = await res.text();
            const lines = text.split('\n');
            lines.forEach(processLine);
            onDone?.();
            setLoading(false);
            setIsThinking(false);
            return;
          }

          // Streaming Mode
          let buffer = "";
          let done = false;
          while (!done) {
            const { value, done: streamDone } = await reader.read();
            if (value) {
              buffer += new TextDecoder().decode(value);
              let lines = buffer.split("\n");
              buffer = lines.pop() || ""; 
              lines.forEach(processLine);
            }
            done = streamDone;
          }
          
          if (buffer.trim()) processLine(buffer);
          
          onDone?.();
          setLoading(false);
          setIsThinking(false);
        })
        .catch((err) => {
          if (err.name === "AbortError") return;
          setError(err);
          setLoading(false);
          setIsThinking(false);
          onError?.(err);
        });
    },
    [apiUrl, accessToken, onToken, onStatus, onMetadata, onFinal, onInterrupt, onToolStart, onToolEnd, onChunk, onDone, onError]
  );

  return { sendMessage, cancel, loading, isThinking, error };
}