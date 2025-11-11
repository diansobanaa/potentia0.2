(DONE)
BELUM DI COBA
📝 TODO List: Implementasi Infrastruktur AI Agent (v3)

Rencana ini akan mengintegrasikan AI Agent (LangChain) ke dalam fondasi v0.4.3 yang sudah ada, dengan fokus khusus pada pemecahan 5 bottleneck yang telah diidentifikasi.

0. Persiapan: Database & Keamanan (Wajib)

Tugas-tugas ini harus diselesaikan sebelum endpoint dapat berfungsi, karena RPC dan endpoint bergantung padanya.

    [ ] Database (S5): Buat file migrasi SQL baru (migration_002_ai_session.sql).

        [ ] Tambahkan kolom generation_session_id UUID NULLABLE ke tabel "blocks". Ini krusial untuk fitur "Undo".

    [ ] Database (W2/LexoRank): Buat fungsi SQL lexorank_generate(prev TEXT, next TEXT, count INT).

        [ ] Ini harus mengimplementasikan logika batch ordering base-62 di dalam plpgsql untuk menghindari pemanggilan LexoRankService 50x.

    [ ] Database (W2): Buat file SQL rpc_bulk_insert_ai_blocks.sql.

        [ ] Salin definisi CREATE FUNCTION rpc_bulk_insert_ai_blocks(...) yang sudah mencakup logika BEGIN/COMMIT, INSERT ... SELECT FROM unnest(), dan INSERT INTO "system_audit".

    [ ] Keamanan (S6): Buat "AI Service User".

        [ ] Buat satu entri pengguna statis di tabel Users (misal: ai_agent@potentia.com).

        [ ] Simpan AI_USER_ID (UUID-nya) sebagai environment variable baru (misal: AI_AGENT_USER_ID).

    [ ] Keamanan (S4): Instal library guardrail (misal: pip install prompt-guard).

Fase 1: Endpoint Streaming (Kolektor Asinkron)

Tugas-tugas ini sebagian besar ada di backend/api/v1/endpoints/canvases.py.

    [ ] Buat Endpoint: Tambahkan POST /api/v1/canvas/{canvas_id}/ai/generate-stream ke canvases.py.

    [ ] Terapkan Keamanan (S3/W4):

        [ ] Lindungi endpoint baru dengan Depends(RedisRateLimiter).

        [ ] Kembangkan RedisRateLimiter untuk membaca user.subscription_tier dan menerapkan batas dinamis.

    [ ] Terapkan Keamanan (S4): Di dalam endpoint, panggil library prompt-guard pada payload prompt yang masuk.

    [ ] Implementasi SSE: Buat endpoint mengembalikan EventSourceResponse.

    [ ] Implementasi Kolektor (W3):

        [ ] Di dalam endpoint SSE, panggil AIAgentService.stream_agent_run (Fase 2).

        [ ] Buat loop async for event in ....

        [ ] Tambahkan logika if event['type'] == 'status': yield ... (untuk feedback "AI Berpikir...").

        [ ] Tambahkan logika if event['type'] == 'tool_output': collected_blocks.append(...).

        [ ] Tambahkan cek batas memori: if len(collected_blocks) > 200: ....

    [ ] Panggil Eksekusi (Fase 3): Setelah loop selesai, panggil query wrapper baru (misal: block_queries.bulk_insert_blocks_rpc(...)) dengan collected_blocks.

Fase 2: "Otak" AI (LangChain Agent)

Tugas-tugas ini ada di file baru backend/app/services/ai_agent_service.py.

    [ ] Buat File: Buat ai_agent_service.py.

    [ ] Definisikan Tools (S1):

        [ ] Impor BlockCreatePayload (atau model Pydantic serupa) sebagai skema validasi.

        [ ] Definisikan tools LangChain (misal: @tool(args_schema=BlockCreatePayload) def create_text(...)).

    [ ] Buat Agent Executor: Inisialisasi AgentExecutor LangChain dengan tools dan model Gemini.

    [ ] Terapkan Retry (W4): Terapkan with_retry() bawaan LangChain pada pemanggilan model Gemini.

    [ ] Implementasi Stream: Buat fungsi stream_agent_run(prompt: str).

        [ ] Panggil agent_executor.astream_events(...).

        [ ] Tulis logika loop untuk men-yield event status dan tool_output.

        [ ] Tulis error handling untuk menangkap on_tool_error dan men-yield event error (S1/W1).

Fase 3: "Tangan" AI (RPC Batch Atomik)

Tugas-tugas ini ada di backend/db/queries/canvas/block_queries.py.

    [ ] Buat Wrapper Python: Buat fungsi Python bulk_insert_blocks_rpc.

    [ ] Panggil RPC: Fungsi ini harus memanggil RPC rpc_bulk_insert_ai_blocks yang baru.

    [ ] Terima Hasil: Fungsi ini harus return response.data (yang akan berisi List[Block] yang baru dibuat).

Fase 4: Broadcast Cerdas (Chunking)

Tugas-tugas ini kembali ke endpoint di canvases.py (Fase 1).

    [ ] Implementasi Chunking (W5):

        [ ] Setelah RPC Fase 3 kembali, ambil all_new_blocks.

        [ ] Tulis logika list comprehension untuk membaginya menjadi chunks (misal: 10 blok per chunk).

    [ ] Loop Broadcast (G1):

        [ ] Tulis loop for chunk in chunks:.

        [ ] Panggil broadcast_to_canvas untuk setiap chunk.

        [ ] Gunakan event type baru: "blocks_bulk_added_chunk".

        [ ] Sertakan generation_session_id di payload broadcast.

        [ ] Tambahkan asyncio.sleep(0.05) di dalam loop.

    [ ] Selesaikan SSE: yield {"type": "complete", "data": all_new_blocks} ke pengguna asli.