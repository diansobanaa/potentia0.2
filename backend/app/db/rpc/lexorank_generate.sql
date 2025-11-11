-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.lexorank_generate(
    p_prev text,
    p_next text,
    p_count integer
);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.lexorank_generate(
    p_prev text,
    p_next text,
    p_count integer
)
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
    v_ranks TEXT[] := ARRAY[]::TEXT[];
    v_base_char TEXT := 'U'; -- 'MID_CHAR'
    v_char_code INT;
BEGIN
    IF p_prev IS NOT NULL THEN
        v_char_code := ascii(substring(p_prev, 1, 1));
        v_base_char := chr(v_char_code + 1);
    END IF;

    FOR i IN 1..p_count LOOP
        v_ranks := array_append(v_ranks, v_base_char || i::TEXT);
    END LOOP;

    RETURN v_ranks;
END;
$$;
