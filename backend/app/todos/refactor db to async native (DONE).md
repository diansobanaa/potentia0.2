(DONE)
📋 TO-DO List: Refaktor Penuh Asinkron (Fase 1-4)

Fase 1: Migrasi Klien Database (Supabase)

Tujuan: Mengganti semua klien Supabase sinkron (Client) dengan klien asinkron (AsyncClient) di titik injeksi dan query.

    [DONE] 1.1. Perbarui Klien Admin (supabase_client.py)

        File: backend/app/db/supabase_client.py

        Tindakan: Ganti create_client dengan create_async_client dan Client dengan AsyncClient.

        Tindakan: Ganti nama fungsi get_supabase_client menjadi get_supabase_admin_async_client agar tujuannya jelas (ini adalah klien admin).

    [DONE] 1.2. Perbarui Injeksi Klien (dependencies.py)

        File: backend/app/core/dependencies.py

        Tindakan (Validasi Token): Ubah get_current_user_and_client untuk menggunakan httpx.AsyncClient atau bungkus panggilan validation_client.get("/user", ...) yang sinkron di dalam await asyncio.to_thread(sync_validate_token) agar tidak memblokir event loop.

        Tindakan (Injeksi Klien):

            Ubah create_client(...) menjadi create_async_client(...).

            Ganti authed_client.options.headers["Authorization"] = ... dengan authed_client.auth.set_session(access_token=token, refresh_token="dummy").

            Tambahkan await pada panggilan profile_response = await authed_client.table("users")...execute().

        Tindakan (Klien Anonim): Ubah supabase_anon_client global menjadi AsyncClient dan inisialisasikan dengan create_async_client di dalam get_current_user_or_guest.

        Tindakan (Kasus Khusus UserService):

            Impor get_supabase_admin_async_client yang baru dari Langkah 1.1.

            Di dalam get_user_service, panggil admin_async_client = get_supabase_admin_async_client().

            Ubah return UserService(...) untuk meng-inject admin_client=admin_async_client.

    [ ] 1.3. Refaktor Query Layer (Pekerjaan Utama)

        File: Semua file .py di dalam direktori berikut:

            backend/app/db/queries/block_queries/

            backend/app/db/queries/calendar/

            backend/app/db/queries/canvas/

            backend/app/db/queries/conversation/

            backend/app/db/queries/workspace/

            backend/app/db/repositories/

        Pola Refaktor:

            Ubah def nama_fungsi(...) menjadi async def nama_fungsi(...).

            Ubah type hint klien dari Client menjadi AsyncClient.

            Hapus semua pembungkus def sync_db_call(): ... dan await asyncio.to_thread(sync_db_call).

            Tambahkan await pada setiap panggilan .execute(). (Contoh: response = await authed_client.table(...).execute()).

        Tindakan (Optimasi): Untuk kueri paginasi (seperti di workspace_queries.py atau canvas_queries.py) yang melakukan 2 kueri (.select() dan .select(count="exact")), gunakan asyncio.gather untuk menjalankannya secara paralel.

    [ ] 1.4. Refaktor Service Layer (Kasus Khusus)

        File: backend/app/services/user/user_service.py

        Tindakan:

            Ubah __init__ untuk menerima admin_client: AsyncClient dari dependency.

            Ganti get_supabase_client() dengan self.admin_client yang baru.

            Ubah def sync_db_calls menjadi async def _async_db_calls.

            Tambahkan await pada semua panggilan .execute() dan .update_user_by_id() di dalam _async_db_calls.

            Hapus await asyncio.to_thread(sync_db_calls) dan ganti dengan updated_user_data = await self._async_db_calls().

        File: backend/app/services/title_stream_service.py

        Tindakan: Ubah def sync_db_call di _update_conversation_title_in_db menjadi async def dan gunakan await self.client.table(...).execute(). Hapus asyncio.to_thread.

        File: backend/app/services/chat_engine/context_manager.py

        Tindakan: Hapus asyncio.to_thread dari semua panggilan kueri dan await langsung (misal: active_context = await context_queries.get_active_context_by_user(...)).

    [ ] 1.5. Refaktor Background Jobs (Jobs)

        File: backend/app/jobs/schedule_expander.py

        Tindakan:

            Ganti from app.db.supabase_client import get_supabase_client dengan from app.db.supabase_client import get_supabase_admin_async_client.

            Ganti admin_client = get_supabase_client() menjadi admin_client = get_supabase_admin_async_client().

            Hapus asyncio.to_thread dari semua pemanggilan kueri (misal: await get_schedule_by_id(...), await bulk_delete_instances_for_schedule(...)).

            PENTING: JANGAN hapus asyncio.to_thread dari panggilan redis_client (redis_client.set, redis_client.delete). Panggilan Redis masih sinkron untuk saat ini.

Fase 2: Migrasi Klien Redis (Bottleneck #2)

Tujuan: Mengganti library redis sinkron dengan redis.asyncio untuk I/O Redis yang non-blocking.

    [DONE] 2.1. Perbarui Dependensi

        File: backend/requirements.txt

        Tindakan: Pastikan redis memiliki versi 4.2.0 atau lebih tinggi (yang menyertakan redis.asyncio). Jika tidak, perbarui menjadi redis[hiredis]>=4.2.0.

    [DONE] 2.2. Perbarui Klien Redis (redis_rate_limiter.py)

        File: backend/app/services/redis_rate_limiter.py

        Tindakan:

            Ubah import redis menjadi import redis.asyncio as redis.

            Klien redis_client yang dibuat oleh redis.from_url sekarang akan menjadi AsyncClient.

            Ubah class RedisRateLimiter menjadi async:

            Ubah def _is_allowed menjadi async def _is_allowed.

            Ubah results = pipe.execute() menjadi results = await pipe.execute().

            Ubah def check_guest_limit dan def check_user_limit menjadi async def dan await self._is_allowed(...).

    [DONE] 2.3. Perbarui Konsumen Redis (freebusy_service.py)

        File: backend/app/services/calendar/freebusy_service.py

        Tindakan:

            self.redis sekarang adalah klien asinkron.

            Hapus def sync_redis_check(): ....

            Ganti cache_results = await asyncio.to_thread(sync_redis_check) dengan cache_results = await pipe.execute().

            Di bagian fallback (pengisian cache), ganti await asyncio.to_thread(redis_pipe.execute) dengan await redis_pipe.execute().

    [DONE] 2.4. Perbarui Konsumen Redis (schedule_expander.py)

        File: backend/app/jobs/schedule_expander.py

        Tindakan: Hapus asyncio.to_thread dari semua panggilan redis_client yang tersisa.

            await asyncio.to_thread(redis_client.set, ...) menjadi await redis_client.set(...).

            await asyncio.to_thread(redis_client.delete, ...) menjadi await redis_client.delete(...).

            await asyncio.to_thread(sync_redis_cleanup) menjadi await pipe.execute() (setelah memindahkan logika pipe keluar dari fungsi sync).

Fase 3: Migrasi Klien Embedding (Bottleneck #3)

Tujuan: Mengganti panggilan embed_content sinkron dengan embed_content_async (jika ada) atau generate_content_async untuk embedding.

    [DONE] 3.1. Analisis embedding_service.py

        File: backend/app/services/embedding_service.py

        Masalah: Klien google-generativeai Anda (genai.embed_content) adalah panggilan blocking.

        Tindakan:

            Ubah _embed_content_sync menjadi _embed_content_async (atau hapus wrappernya).

            Di dalam async def generate_embedding, ganti await asyncio.to_thread(_embed_content_sync, ...) dengan:
            Python

            try:
                result = await genai.embed_content_async(
                    model="models/text-embedding-004",
                    content=text,
                    task_type=task_type
                )
                return result["embedding"]
            except Exception as e:
                logger.error(f"Error internal saat memanggil genai.embed_content_async: {e}", exc_info=True)
                raise EmbeddingGenerationError(str(e))

        Catatan: Ini mengasumsikan genai.embed_content_async ada di versi library Anda. Jika tidak ada, biarkan implementasi asyncio.to_thread saat ini; itu sudah merupakan solusi terbaik untuk I/O blocking.

Fase 4: Validasi dan Pembersihan

    [ ] 4.1. Verifikasi Kode

        Tindakan: Lakukan pencarian global (Search) di seluruh codebase Anda untuk string "asyncio.to_thread".

    [ ] 4.2. Tinjau Hasil

        Hasil Ideal: Tidak ada lagi pemanggilan asyncio.to_thread.

        Hasil Realistis (Jika Fase 3 Gagal): Satu-satunya pemanggilan yang tersisa adalah di app/services/embedding_service.py, yang dapat diterima jika tidak ada alternatif asinkron native.

        Hasil Realistis (Jika Validasi Token Dibiarkan): Mungkin ada satu pemanggilan di app/core/dependencies.py untuk validasi token httpx, yang juga dapat diterima.


backend\app\db\queries\workspace\workspace_queries.py
backend\app\services\user\user_service.py
backend\app\services\chat_engine\context_manager.py
backend\app\services\title_stream_service.py
backend\app\jobs\schedule_expander.py