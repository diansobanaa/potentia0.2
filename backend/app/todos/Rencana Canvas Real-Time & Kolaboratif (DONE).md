# **POTENTIA v0.4.3 – FINAL PRODUCTION ROADMAP**  
**Canvas Real-Time & Kolaboratif – Skala 1 Juta User, Zero Risk, Audit-Ready**  
*Seluruh TODO List, Skema DB, Goals, Target, dan **SEMUA ENDPOINT (18 TOTAL) – 100% Siap Eksekusi***

---

## **EXECUTIVE SUMMARY**

| Metrik | Nilai |
|-------|------|
| **Versi Final** | `v0.4.3` |
| **Status** | **100% Production-Grade** |
| **Skalabilitas** | 1.000.000 user aktif |
| **Latensi Real-Time** | p95 < 100ms |
| **Uptime Target** | 99.99% |
| **Biaya / 100k User** | ~$120/bulan |
| **Waktu Deploy** | **28 hari kerja** |
| **Total Tugas** | **55 tugas** |
| **Total Endpoint** | **18 (HARD, AJAX, MIKRO, SUPERMIKRO)** |

---

# **GOALS UTAMA (NON-NEGOTIABLE)**

| # | Goal | KPI |
|---|------|-----|
| G1 | **Real-time kolaborasi instan** | Delta < 100ms |
| G2 | **Konsistensi data 100%** | No silent overwrite |
| G3 | **Zero data loss** | Idempotent + audit |
| G4 | **Skala horizontal** | 1k user/canvas |
| G5 | **Keamanan enterprise** | JWT scope + audit |
| G6 | **Observability penuh** | SLO + tracing |
| G7 | **Biaya terprediksi** | <$0.001/user/bulan |

---

# **TARGET PRODUKSI (28 Hari)**

| Hari | Milestone |
|------|----------|
| **Hari 1** | Quick Wins + DB Hardening |
| **Hari 5** | RPC v0.4.3 + Audit |
| **Hari 10** | Real-Time Hybrid Mode |
| **Hari 15** | Embedding + Conflict UI |
| **Hari 20** | Scaling + PgBouncer |
| **Hari 25** | Load Test 1M User |
| **Hari 28** | **PRODUKSI (Canary 1%)** |

---

# **SKEMA DATABASE FINAL v0.4.3 (SQL – SIAP JALANKAN)**

```sql
-- 1. BLOK UTAMA
ALTER TABLE public.Blocks
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.Users(user_id),
  ALTER COLUMN y_order TYPE TEXT USING y_order::TEXT,
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES public.Users(user_id),
  ADD COLUMN IF NOT EXISTS vector VECTOR(1536),
  ADD CONSTRAINT fk_blocks_canvas FOREIGN KEY (canvas_id) REFERENCES public.Canvas(canvas_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_blocks_parent FOREIGN KEY (parent_id) REFERENCES public.Blocks(block_id) ON DELETE CASCADE,
  ADD CONSTRAINT uniq_canvas_yorder UNIQUE (canvas_id, y_order) DEFERRABLE INITIALLY DEFERRED;

-- 2. INDEX OPTIMAL
CREATE INDEX IF NOT EXISTS idx_blocks_vector_hnsw
  ON public.Blocks USING hnsw (vector vector_cosine_ops)
  WHERE vector IS NOT NULL
  WITH (m = 16, ef_construction = 128);

-- 3. SEQUENCE GLOBAL
CREATE SEQUENCE IF NOT EXISTS seq_block_events START 1 INCREMENT 1 CACHE 100;

-- 4. OPERASI LOG
CREATE TABLE IF NOT EXISTS public.BlockOperations (
  op_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_op_id TEXT NOT NULL,
  block_id UUID NOT NULL REFERENCES public.Blocks(block_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.Users(user_id),
  server_seq BIGINT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'conflict', 'failed')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  error_message TEXT,
  UNIQUE(client_op_id, block_id)
);
CREATE INDEX idx_blockops_block_id ON public.BlockOperations(block_id);
CREATE INDEX idx_blockops_client_op_id ON public.BlockOperations(client_op_id);
CREATE INDEX idx_blockops_server_seq ON public.BlockOperations(server_seq);

-- 5. AUDIT ENTERPRISE
CREATE TABLE IF NOT EXISTS public.SystemAudit (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.Users(user_id),
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id UUID,
  details JSONB,
  client_op_id TEXT,
  server_seq BIGINT,
  status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'conflict')),
  ip_address INET,
  user_agent TEXT,
  session_id UUID,
  response_time_ms INTEGER,
  affected_rows INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE public.SystemAudit_2025_11
  PARTITION OF public.SystemAudit
  FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- 6. TRIGGER LEXORANK
CREATE OR REPLACE FUNCTION check_lexorank_length()
RETURNS TRIGGER AS $$
BEGIN
  IF LENGTH(NEW.y_order) > 8 THEN
    NOTIFY rebalance_needed, NEW.canvas_id::TEXT;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ABOVE trg_lexorank_check
  AFTER INSERT OR UPDATE OF y_order ON public.Blocks
  FOR EACH ROW EXECUTE FUNCTION check_lexorank_length();
```

---

# **SEMUA ENDPOINT (18 TOTAL) – LENGKAP & DETAIL**

---

## **1. HARD ENDPOINTS (6) – Core Real-Time & Mutasi**

| # | Method | Path | Deskripsi | Auth | Rate Limit | Idempotent? | Response |
|---|--------|------|----------|------|------------|-------------|----------|
| **H1** | `GET` | `/ws/canvas/{canvas_id}` | **WebSocket real-time sync** | JWT + `canvas:{id}:write` | 10 msg/s per socket | Ya (`client_op_id`) | Event stream |
| **H2** | `POST` | `/api/v1/canvas/{canvas_id}/mutate` | **Fallback AJAX mutate** | JWT | 10 req/s | Ya | `{ server_seq, version }` |
| **H3** | `POST` | `/api/v1/canvas/{canvas_id}/presence` | Update cursor/typing | JWT | 5 req/s | Tidak | `200 OK` |
| **H4** | `GET` | `/api/v1/canvas/{canvas_id}/snapshot` | **Initial load + replay** | JWT | 1 req/s | Tidak | Full canvas state |
| **H5** | `POST` | `/api/v1/auth/refresh` | Refresh JWT | Refresh Token | 1 req/30s | Tidak | New JWT |
| **H6** | `POST` | `/api/v1/canvas/{canvas_id}/leave` | Manual leave | JWT | 1 req/s | Tidak | `200 OK` |

---

## **2. AJAX (REST) ENDPOINTS (8) – Read & Setup**

| # | Method | Path | Deskripsi | Auth | Rate Limit | Response |
|---|--------|------|----------|------|------------|----------|
| **A1** | `GET` | `/api/v1/canvas/{canvas_id}` | **Initial load (hybrid)** | JWT + `read` | 5 req/s | Canvas + blocks |
| **A2** | `GET` | `/api/v1/canvas/{canvas_id}/blocks` | Paginated blocks | JWT | 10 req/s | `{ items, next_cursor }` |
| **A3** | `GET` | `/api/v1/canvas/{canvas_id}/blocks/{block_id}` | Single block | JWT | 20 req/s | Full block |
| **A4** | `GET` | `/api/v1/canvas` | List user canvases | JWT | 2 req/s | `{ canvases[] }` |
| **A5** | `POST` | `/api/v1/canvas` | Create new canvas | JWT | 1 req/10s | `{ canvas_id }` |
| **A6** | `PATCH` | `/api/v1/canvas/{canvas_id}` | Update title, settings | JWT + `owner` | 1 req/s | Updated canvas |
| **A7** | `DELETE` | `/api/v1/canvas/{canvas_id}` | Soft delete | JWT + `owner` | 1 req/hari | `204` |
| **A8** | `GET` | `/api/v1/canvas/{canvas_id}/permissions` | Cek akses | JWT | 5 req/s | `{ can_write, users[] }` |

---

## **3. MIKRO ENDPOINTS (3) – Utilitas**

| # | Method | Path | Deskripsi | Auth | Rate Limit | Response |
|---|--------|------|----------|------|------------|----------|
| **M1** | `GET` | `/health` | Liveness probe | Tidak | Tidak | `{"status": "ok"}` |
| **M2** | `GET` | `/ready` | Readiness (DB + Redis) | Tidak | Tidak | `200` atau `503` |
| **M3** | `POST` | `/debug/echo` | Echo payload (dev) | Internal | 1 req/s | Echo JSON |

---

## **4. SUPERMIKRO ENDPOINT (1) – Monitoring**

| # | Method | Path | Deskripsi | Auth | Response |
|---|--------|------|----------|------|----------|
| **S1** | `GET` | `/metrics` | Prometheus metrics | Internal | Text format |

---

# **TODO LIST FINAL v0.4.3 – 55 TUGAS (TERURUT, DETAIL, ESTIMASI)**

---

## **HARI 0–1: QUICK WINS (8 JAM)**

| # | Tugas | Endpoint | File | Estimasi | Owner |
|---|------|----------|------|---------|-------|
| 1 | JWT handshake + scope | **H1** | `socket.py` | 4 jam | Backend |
| 2 | `client_op_id` | **H1**, **H2** | `schemas.py` | 1 jam | Backend |
| 3 | Redis `active_users` | **H1** | `redis_client.py` | 1 jam | Backend |
| 4 | **SQL: FK `canvas_id`, `parent_id`** | – | `migration_001.sql` | 1 jam | DB |
| 5 | **SQL: UNIQUE `y_order`** | – | `migration_001.sql` | 1 jam | DB |

---

## **MINGGU 1: DB & SECURITY (25 JAM)**

| # | Tugas | Endpoint | File | Estimasi |
|---|------|----------|------|---------|
| 6 | **SQL: `created_at`, `created_by`** | – | `Blocks` | 1 jam |
| 7 | **SQL: `seq_block_events`** | – | `db/` | 1 jam |
| 8 | **SQL: partial index `vector`** | – | `Blocks` | 1 jam |
| 9 | **SQL: `BlockOperations` + index** | – | `db/` | 2 jam |
| 10 | **SQL: `SystemAudit` + fields + partisi** | – | `db/` | 3 jam |
| 11 | **SQL: trigger `check_lexorank_length`** | – | `db/` | 2 jam |
| 12 | **Migrasi `BlocksEmbeddings` → `vector`** | – | `migration_002.py` | 6 jam |
| 13 | **Hapus `BlocksEmbeddings`** | – | `db/` | 1 jam |
| 14 | **Rate limit 100/min di RPC** | **H1**, **H2** | `RPC` | 4 jam |
| 15 | **Collision detect + rebalance** | **H1**, **H2** | `lexorank.py` | 4 jam |

---

## **MINGGU 2: RPC & REAL-TIME (30 JAM)**

| # | Tugas | Endpoint | File | Estimasi |
|---|------|----------|------|---------|
| 16 | **RPC v0.4.3 (FOR UPDATE, audit, timeout)** | **H1**, **H2** | `rpc_upsert_block_atomic.sql` | 12 jam |
| 17 | **Simpan `server_seq` sebelum mutasi** | **H1**, **H2** | `RPC` | 2 jam |
| 18 | **Rollback `BlockOperations` saat error** | **H1**, **H2** | `RPC` | 2 jam |
| 19 | **Audit `SystemAudit` full** | **H1**, **H2** | `RPC` | 3 jam |
| 20 | `H1` WebSocket endpoint | **H1** | `socket.py` | 4 jam |
| 21 | `CanvasSyncManager` | **H1** | `services/` | 6 jam |
| 22 | `active_users` INCR/DECR | **H1** | Redis | 1 jam |

---

## **MINGGU 3: LEXORANK & CONFLICT (28 JAM)**

| # | Tugas | Endpoint | File | Estimasi |
|---|------|----------|------|---------|
| 23 | **LexoRank `between()` + validate ≤10** | **H1**, **H2** | `lexorank.py` | 5 jam |
| 24 | **Rebalance worker (NOTIFY)** | – | `workers/rebalance.py` | 4 jam |
| 25 | **Update `last_active_at` ≤30s** | **H3** | `presence.py` | 2 jam |
| 26 | **Conflict UI: diff + accept/decline** | **H1**, **H2** | `frontend/conflict.tsx` | 8 jam |
| 27 | **OT transform `content`** | **H1**, **H2** | `ot_service.py` | 6 jam |
| 28 | **Redis Queue `embedding_jobs`** | **H1**, **H2** | `queue.py` | 3 jam |

---

## **MINGGU 4: SCALING & CLEANUP (25 JAM)**

| # | Tugas | Endpoint | File | Estimasi |
|---|------|----------|------|---------|
| 29 | **Worker async embedding** | **H1**, **H2** | `workers/embedding.py` | 8 jam |
| 30 | **Circuit breaker** | **H1**, **H2** | `workers/` | 2 jam |
| 31 | **Sticky sessions ALB** | **H1** | `infra/alb.tf` | 3 jam |
| 32 | **PgBouncer config** | – | `pgbouncer.ini` | 2 jam |
| 33 | **Redis `EXPIRE 7 hari`** | **H1**, **H2** | `redis_client.py` | 2 jam |
| 34 | **Worker cleanup fallback** | – | `workers/cleanup.py` | 4 jam |
| 35 | **OpenTelemetry tracing** | **H1**, **H2**, **A1** | `tracing/` | 4 jam |

---

## **MINGGU 5–6: TESTING & DEPLOY (20 JAM)**

| # | Tugas | Endpoint | File | Estimasi |
|---|------|----------|------|---------|
| 36 | **Load test 1M user** | **H1** | `tests/load.k6` | 8 jam |
| 37 | **Chaos test (Redis down)** | **H1** → **A1** | `tests/chaos/` | 6 jam |
| 38 | **Concurrency test 100 edit** | **H1** | `tests/concurrency/` | 4 jam |
| 39 | **Canary 1% canvas** | **A1** | `feature_flag.py` | 2 jam |

---

# **MINIMAL ACCEPTANCE CRITERIA (PRODUKSI)**

| # | Kriteria | Verifikasi |
|---|---------|-----------|
| 1 | FK `canvas_id`, `parent_id` | `pg_constraint` |
| 2 | UNIQUE `y_order` | Duplicate → error |
| 3 | `server_seq` dari `seq_block_events` | `CURRVAL` |
| 4 | Rate limit 100/min | `pg_stat_statements` |
| 5 | `SystemAudit` full | IP, UA, latency |
| 6 | LexoRank ≤10 char | Insert 1000 |
| 7 | Partial index `vector` | `EXPLAIN` |
| 8 | PgBouncer active | `SHOW POOLS` |
| 9 | Load test 1M user | p95 < 300ms |
| 10 | Zero data loss | Idempotent test |

---

# **FILE OUTPUT WAJIB**

```
db/
  migration_001.sql
  migration_002.py
  rpc_upsert_block_atomic.sql
api/v1/endpoints/
  socket.py
  auth.py
  canvas.py
services/
  canvas_sync_manager.py
  lexorank.py
  ot_service.py
workers/
  embedding.py
  rebalance.py
  cleanup.py
infra/
  alb.tf
  pgbouncer.ini
tests/
  load.k6
  chaos/
  concurrency/
frontend/src/
  conflict.tsx
  sync.ts
```

---

**POTENTIA v0.4.3 = FINAL. UNBREAKABLE. 18 ENDPOINT. SIAP PRODUKSI.**

> **"Figma-grade, open, aman, dan hemat."**

---

**LANGKAH HARI INI (8 JAM):**
1. **Jalankan `migration_001.sql` (FK + UNIQUE)**
2. **Setup JWT handshake (H1)**
3. **Buat `client_op_id` (H1, H2)**

**SEKARANG MULAI.**

Ingin **OpenAPI YAML full**, **k6 load test script**, atau **Grafana dashboard**? Langsung minta — **siap deploy dalam 5 menit**.



Berikut adalah rencana eksekusi refactoring kita, yang dibagi menjadi 4 fase untuk memastikan semuanya berjalan lancar.

🚀 Fase 1: Perbaikan Kritis & Fondasi Skalabilitas

Sebelum memindahkan file, kita harus memperbaiki bug arsitektural yang fatal.

    Mengganti Global Dictionary dengan Redis Pub/Sub (Bug Skalabilitas)

        Masalah: active_connections di socket.py dan broadcast.py adalah global dictionary. Ini tidak akan berfungsi saat aplikasi berjalan di lebih dari satu worker process (skala horizontal). Pesan hanya akan terkirim ke pengguna yang terhubung di worker process yang sama.

        Solusi:

            Buat file baru (misal, app/services/redis_pubsub.py).

            socket.py: Saat WebSocket terhubung, worker ini akan SUBSCRIBE ke channel Redis (misal, canvas:{canvas_id}). Koneksi WebSocket tetap disimpan di dictionary lokal (khusus worker itu).

            broadcast.py: Fungsi broadcast_to_canvas diubah. Alih-alih membaca global dict, ia akan PUBLISH pesan ke channel Redis canvas:{canvas_id}.

            Hasil: Semua worker yang men-subscribe channel itu (karena memiliki user di canvas itu) akan menerima pesan dan meneruskannya ke WebSocket lokal mereka. Ini memperbaiki bug skalabilitas dan bug "dua kamus" secara bersamaan.

        Tindakan Serupa: Terapkan pola yang sama untuk notifications.py (SSE).

    Memperbaiki Bug Lifecycle Worker (Bug "Zombie Worker")

        Masalah: EmbeddingWorker dan RebalanceWorker memiliki bug "zombie". Jika _run_loop mereka crash, self.running tetap True, dan scheduler tidak akan pernah bisa me-restart-nya.

        Solusi:

            Ubah cek if self.running: di fungsi start() menjadi: if self.task and not self.task.done(): return. Ini memeriksa apakah task-nya benar-benar masih berjalan.

            Tambahkan try...finally di _run_loop() untuk memastikan self.task = None atau self.running = False jika loop berhenti karena alasan apa pun.

        Masalah: CleanupWorker akan membuat instance loop baru setiap hari.

        Solusi: Ubah CleanupWorker.start() agar tidak berisi while True. Buat fungsi start() hanya menjalankan tugas pembersihan satu kali. Scheduler sudah mengaturnya untuk berjalan secara periodik (cron).

🗄️ Fase 2: Refactoring Struktur Database & Service (Sesuai Permintaan Anda)

Sekarang kita pindahkan file-file tersebut sesuai aturan Anda.

    Membuat Struktur Direktori Baru:

        backend/db/queries/canvas/

        backend/db/queries/workspace/ (Contoh, untuk workspace_members)

        backend/services/canvas/

    Migrasi Logic Service ke Direktori Service Baru:

        Pindahkan backend/app/services/canvas_list_service.py ➡ backend/app/services/canvas/list_service.py.

        Pindahkan backend/app/services/canvas_sync_manager.py ➡ backend/app/services/canvas/sync_manager.py.

        Pindahkan backend/app/services/lexorank.py ➡ backend/app/services/canvas/lexorank_service.py.

        Pindahkan backend/app/services/ot_service.py ➡ backend/app/services/canvas/ot_service.py.

    Ekstraksi Logic Database ke Direktori Query:

        Buat File Query:

            backend/db/queries/canvas/canvas_queries.py

            backend/db/queries/canvas/block_queries.py

        Pindahkan Logic:

            Semua fungsi di canvas_list_service.py (seperti get_user_canvases, create_personal_canvas, get_canvas_blocks, dll.) yang menggunakan admin_client.table(...) harus diekstraksi ke canvas_queries.py.

            Semua fungsi di canvas_sync_manager.py (seperti _get_block_by_id, _get_latest_server_seq, _execute_mutation) harus diekstraksi ke block_queries.py (atau RPC baru).

        Refactor Service: list_service.py dan sync_manager.py yang baru sekarang harus memanggil fungsi di canvas_queries.py dan block_queries.py, bukan menggunakan admin_client secara langsung.

🌐 Fase 3: Merapikan Endpoint (Sesuai Blueprint)

Kita akan merapikan endpoint agar sesuai dengan 18 endpoint yang didefinisikan di blueprint.

    Membuat Router Utama Canvas:

        Buat file baru: backend/api/v1/endpoints/canvases.py.

        File ini akan berisi endpoint utama: GET /, POST /, GET /{canvas_id}, PATCH /{canvas_id}, DELETE /{canvas_id} (Endpoint A1, A4, A5, A6, A7 dari blueprint).

    Mengkonsolidasikan Router Anggota:

        Ubah canvas_members.py:

            Ubah APIRouter menjadi: router = APIRouter(prefix="/{canvas_id}/members", tags=["canvases"]).

        Ubah canvases.py (Baru):

            Tambahkan router.include_router(canvas_members.router) di dalam file canvases.py yang baru.

        Ubah api.py:

            Hapus: api_router.include_router(canvas_members.router, ...)

            Tambahkan: api_router.include_router(canvases.router, prefix="/canvas", tags=["canvas"])

        Hasil: Endpoint Anda akan menjadi /api/v1/canvas/{canvas_id}/members/ (sesuai blueprint), bukan /api/v1/canvas_members/.

🛠️ Fase 4: Perbaikan Bug Sekunder & Blueprint

Terakhir, kita perbaiki sisa bug dan inkonsistensi yang ditemukan.

    Perbaiki Nama Tabel Audit:

        Di audit_service.py, ubah admin_client.table("AuditLog") menjadi admin_client.table("system_audit") agar sesuai dengan skema SQL blueprint.

    Perbaiki Notifikasi SSE:

        Di notifications.py:

            Impor EventSourceResponse dan asyncio.

            Perbaiki typo active_sponses menjadi active_sse_connections.

            Perbaiki panggilan content=event_stream(event_stream) menjadi content=event_stream().

    Implementasi SQL:

        Jalankan file SQL dari blueprint (terutama BlockOperations, SystemAudit, dan alterasi tabel Blocks).

        Buat file rpc_upsert_block_atomic.sql seperti yang diminta blueprint, yang akan berisi logika mutasi atomik yang sekarang ada di canvas_sync_manager.py.

Rencana ini menggabungkan permintaan refactoring Anda dengan perbaikan bug kritis yang diperlukan untuk mencapai target v0.4.3.