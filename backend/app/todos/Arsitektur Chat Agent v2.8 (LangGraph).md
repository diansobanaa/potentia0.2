# Arsitektur Chat Agent v2.8 (LangGraph - Production Ready)

Dokumen ini adalah "sumber kebenaran" (source of truth) untuk arsitektur fitur chat AI Potentia.

Arsitektur ini menggantikan arsitektur v1 "3-Panggilan" (`ChatService`, `JudgeChain`, `LLMExecutor`) yang kaku dan boros.

## Goals Utama (v2.8)

1.  **Agen Proaktif:** (Goal #1) AI dapat secara proaktif memanggil *tools* (misal: `create_schedule_tool`) untuk membantu pengguna.
2.  **RAG Holistik:** (Goal #2) AI memiliki "ingatan" dengan memanggil RPC RAG holistik (`rpc_find_relevant_blocks_holistic` dan `find_relevant_summaries`) yang mencari di *semua* data pengguna.
3.  **Tangguh (Resilient):** (NFR Poin 4) Panggilan LLM/Tool memiliki *retry* dan *timeout*.
4.  **Aman (Secure):** (NFR Poin 3) *Tools* dijalankan melalui `ToolExecutor` yang memeriksa izin (`permissions`) dari `AgentState`.
5.  **Durable (HiTL):** (NFR Poin 11) *State* disimpan di Redis (`RedisSaver`). *Graph* dapat dijeda (`InterruptException`) untuk persetujuan manusia dan dilanjutkan (`resume`) melalui API.
6.  **Efisien (Token & Biaya):** (NFR Poin 8, 9)
    * *Reranking* menggunakan Gemini Flash (murah), bukan Cohere.
    * Ekstraksi preferensi dipisah ke *node* (Flash) sendiri.
    * *Token count* dilacak dan disimpan ke database.
7.  **Performa (UX):** (NFR Poin 8) *Endpoint* `chat.py` menggunakan `astream_events` untuk *streaming token-demi-token* (mengurangi *perceived latency*).

## File Inti Arsitektur v2.8

Arsitektur ini berpusat pada 5 file utama di `backend/app/services/chat_engine/`:

1.  **`agent_state.py`**:
    * Definisi `TypedDict` (`AgentState`). Ini adalah "darah" yang mengalir di *graph* dan disimpan di Redis. Berisi `request_id`, `user_id`, `permissions`, `chat_history`, `rag_query`, `final_response`, dll.

2.  **`agent_prompts.py`**:
    * Menyimpan semua *prompt* (sebagai `str`) untuk setiap *node* (NFR Poin 7).
    * Contoh: `CLASSIFY_INTENT_PROMPT`, `AGENT_SYSTEM_PROMPT`, `RERANK_GEMINI_PROMPT`.

3.  **`llm_client.py`**:
    * *Wrapper* terpusat untuk memanggil model Gemini (NFR Poin 12).
    * Mengimplementasikan *retry*, *timeout*, dan *metrics* Prometheus (NFR Poin 2, 4).
    * Menyediakan `llm_flash_client` (untuk RAG/Klasifikasi) dan `llm_pro_client` (untuk jawaban).

4.  **`tool_executor.py`**:
    * *Wrapper* terpusat untuk eksekusi *tool* (NFR Poin 12).
    * Mengimplementasikan **Keamanan** (memeriksa `state['permissions']`) (NFR Poin 3).
    * Meneruskan `request_id` ke *tools* untuk **Idempotency** (NFR Poin 5).
    * Mencatat *metrics* tool.

5.  **`langgraph_agent.py`**:
    * Ini adalah **otak** utama. File ini mendefinisikan `StateGraph`.
    * Mendefinisikan semua *node* (`classify_intent`, `retrieve_context`, `rerank_context`, `agent_node`, `reflection_node`, `call_tools`, `extract_preferences_node`).
    * Mendefinisikan *alur* (edges) dan *router* kondisional.
    * Mengompilasi *graph* dengan `RedisSaver` (Checkpointer).

## Alur Eksekusi (Contoh RAG)



1.  `chat.py` (API) menerima permintaan.
2.  `chat.py` membuat `initial_state` (mengisi `user_id`, `permissions`, `chat_history`).
3.  `chat.py` meng-inject dependensi (`auth_info`, `embedding_service`) ke `RunnableConfig`.
4.  `chat.py` memanggil `langgraph_agent.astream_events(...)`.
5.  *Graph* berjalan:
    1.  `sanitize_input` (Membersihkan `user_message`).
    2.  `classify_intent` (Memanggil Flash LLM -> "rag_query").
    3.  `query_transform` (Memanggil Flash LLM -> `rag_query` & `ts_query`).
    4.  `retrieve_context` (Memanggil RPC RAG Holistik).
    5.  `rerank_context` (Memanggil Flash LLM untuk *rerank*).
    6.  `context_compression` (Memanggil Flash LLM untuk meringkas).
    7.  `agent_node` (Memanggil Pro LLM untuk *streaming* jawaban).
    8.  `extract_preferences_node` (Memanggil Flash LLM untuk ekstraksi JSON).
    9.  `END`.
6.  `chat.py` (stream generator) mengirim *chunk* token ke UI.
7.  `chat.py` (background task) menyimpan pesan + *token count* ke `public.messages`.