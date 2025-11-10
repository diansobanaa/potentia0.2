-- File: backend/db/migrations/migration_001_v0.4.3.sql
-- (Menggabungkan SEMUA skema SQL dari Blueprint v0.4.3)

BEGIN;

-- 1. BLOK UTAMA (dari Blueprint)
-- Memperbarui tabel Blocks yang ada
ALTER TABLE public.Blocks
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.Users(user_id) ON DELETE SET NULL,
  ALTER COLUMN y_order TYPE TEXT USING y_order::TEXT,
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES public.Users(user_id) ON DELETE SET NULL,
  
  -- !! PERBAIKAN KRITIS !!
  -- Blueprint menyebutkan VECTOR(1536) (OpenAI).
  -- Kode Anda (embedding_service.py) menggunakan
  -- Gemini 'text-embedding-004' yang menghasilkan 768 dimensi.
  -- Menggunakan 768 untuk mencocokkan kode Anda.
  ADD COLUMN IF NOT EXISTS vector VECTOR(768), 
  
  ADD CONSTRAINT IF NOT EXISTS fk_blocks_canvas FOREIGN KEY (canvas_id) REFERENCES public.Canvas(canvas_id) ON DELETE CASCADE,
  ADD CONSTRAINT IF NOT EXISTS fk_blocks_parent FOREIGN KEY (parent_id) REFERENCES public.Blocks(block_id) ON DELETE CASCADE;
  -- ADD CONSTRAINT IF NOT EXISTS uniq_canvas_yorder UNIQUE (canvas_id, y_order) DEFERRABLE INITIALLY DEFERRED;
  -- Catatan: UNIQUE(canvas_id, y_order) mungkin menyebabkan masalah
  -- saat rebalance. Pertimbangkan ulang jika diperlukan.

-- 2. INDEX OPTIMAL (dari Blueprint)
-- Pastikan ekstensi 'vector' diaktifkan di Supabase
CREATE INDEX IF NOT EXISTS idx_blocks_vector_hnsw
  ON public.Blocks USING hnsw (vector vector_cosine_ops)
  WHERE vector IS NOT NULL
  WITH (m = 16, ef_construction = 128);

-- 3. SEQUENCE GLOBAL (dari Blueprint)
CREATE SEQUENCE IF NOT EXISTS seq_block_events START 1 INCREMENT 1 CACHE 100;

-- 4. OPERASI LOG (dari Blueprint)
CREATE TABLE IF NOT EXISTS public.BlockOperations (
  op_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_op_id TEXT NOT NULL,
  block_id UUID NOT NULL, -- Tidak bisa FK ke Blocks ON DELETE CASCADE jika kita ingin log penghapusan
  user_id UUID NOT NULL REFERENCES public.Users(user_id),
  canvas_id UUID NOT NULL REFERENCES public.Canvas(canvas_id) ON DELETE CASCADE,
  server_seq BIGINT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'conflict', 'failed')),
  payload JSONB, -- Data yang dikirim klien
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  error_message TEXT,
  UNIQUE(client_op_id, block_id)
);
CREATE INDEX IF NOT EXISTS idx_blockops_block_id ON public.BlockOperations(block_id);
CREATE INDEX IF NOT EXISTS idx_blockops_canvas_id ON public.BlockOperations(canvas_id);
CREATE INDEX IF NOT EXISTS idx_blockops_server_seq ON public.BlockOperations(server_seq);

-- 5. AUDIT ENTERPRISE (dari Blueprint)
-- Menggunakan nama 'SystemAudit' dari blueprint, bukan 'AuditLog'
CREATE TABLE IF NOT EXISTS public.SystemAudit (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.Users(user_id), -- Bisa NULL untuk sistem
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
);
-- (Partisi dihilangkan untuk kesederhanaan, bisa ditambahkan nanti)

-- 6. TRIGGER LEXORANK (dari Blueprint)
CREATE OR REPLACE FUNCTION check_lexorank_length()
RETURNS TRIGGER AS $$
BEGIN
  IF LENGTH(NEW.y_order) > 8 THEN
    -- Mengirim notifikasi ke channel 'rebalance_needed'
    -- Worker 'rebalance.py' harus MENDENGARKAN channel ini.
    PERFORM pg_notify('rebalance_needed', json_build_object('canvas_id', NEW.canvas_id)::TEXT);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lexorank_check
  AFTER INSERT OR UPDATE OF y_order ON public.Blocks
  FOR EACH ROW EXECUTE FUNCTION check_lexorank_length();

COMMIT;