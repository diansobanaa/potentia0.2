-- File: backend/app/db/migrations/migration_003_chat_v3_0.sql
-- (File Baru v3.0 - Menyelesaikan NFR Poin 8 & Goal 'chatgpt flow')

BEGIN;

-- Menambahkan kolom untuk melacak penggunaan token per pesan (Perbaikan Gap #1)
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS input_tokens INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS output_tokens INTEGER DEFAULT 0;

COMMENT ON COLUMN public.messages.input_tokens IS 'Jumlah token di prompt yang menghasilkan pesan ini (hanya untuk role=assistant).';
COMMENT ON COLUMN public.messages.output_tokens IS 'Jumlah token di konten pesan ini (hanya untuk role=assistant).';

-- [PERBAIKAN Gap #7] Modifikasi 'summary_memory' untuk 'chatgpt flow'
-- Hapus 'context_id' yang usang dan tambahkan 'conversation_id'
ALTER TABLE public.summary_memory
  DROP CONSTRAINT IF EXISTS summary_memory_context_id_fkey,
  DROP COLUMN IF EXISTS context_id,
  ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES public.conversations(conversation_id) ON DELETE CASCADE;

-- Tambahkan index untuk pencarian cepat berdasarkan conversation
CREATE INDEX IF NOT EXISTS idx_summary_memory_conversation_id ON public.summary_memory(conversation_id);

-- [PERBAIKAN Gap #6] Hapus RPC lama yang salah
DROP FUNCTION IF EXISTS public.find_similar_blocks(
    p_canvas_id uuid,
    p_query_embedding vector,
    p_limit integer
);

COMMIT;