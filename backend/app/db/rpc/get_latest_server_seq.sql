-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.get_latest_server_seq(p_canvas_id uuid);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.get_latest_server_seq(p_canvas_id uuid)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_latest_seq BIGINT;
BEGIN
    SELECT 
        MAX(server_seq) INTO v_latest_seq
    FROM 
        public.block_operations bo -- DIUBAH
    JOIN 
        public.blocks b ON bo.block_id = b.block_id -- DIUBAH
    WHERE 
        b.canvas_id = p_canvas_id;
    
    RETURN COALESCE(v_latest_seq, 0);
END;
$$;
