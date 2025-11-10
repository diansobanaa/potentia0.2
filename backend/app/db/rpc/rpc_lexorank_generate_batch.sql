-- CATATAN: Ini adalah implementasi 'plpgsql' yang disederhanakan dari
-- logika base-62 Anda. 
-- Ini menghasilkan 'U', 'V', 'W' ...
CREATE OR REPLACE FUNCTION lexorank_generate(
    p_prev TEXT,
    p_next TEXT,
    p_count INT
)
RETURNS TEXT[] AS $$
DECLARE
    v_ranks TEXT[] := ARRAY[]::TEXT[];
    v_base_char TEXT := 'U'; -- 'MID_CHAR'
    v_char_code INT;
BEGIN
    -- Logika _increment sederhana jika 'prev' ada
    IF p_prev IS NOT NULL THEN
        v_char_code := ascii(substring(p_prev, 1, 1));
        v_base_char := chr(v_char_code + 1);
    END IF;

    -- Hasilkan 'count' rank baru
    FOR i IN 1..p_count LOOP
        v_ranks := array_append(v_ranks, v_base_char || i::TEXT);
    END LOOP;

    RETURN v_ranks;
END;
$$ LANGUAGE plpgsql;