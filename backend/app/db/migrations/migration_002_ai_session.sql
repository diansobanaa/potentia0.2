ALTER TABLE public."Blocks"
ADD COLUMN IF NOT EXISTS generation_session_id UUID NULLABLE;

COMMENT ON COLUMN public."Blocks".generation_session_id IS 
'UUID Sesi unik untuk melacak blok yang dibuat oleh satu panggilan AI (untuk fitur Undo).';