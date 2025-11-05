-- PARSE: 05-create-domain-v1.sql
-- Keterangan: Dijalankan sekali untuk mendefinisikan tipe vektor di seluruh aplikasi.
-- Ini menyelesaikan masalah hardcoding dimensi vektor.
CREATE DOMAIN public.app_vector AS vector(768);


1. Fungsi: find_relevant_role_id

Deskripsi

Fungsi ini adalah Router Peran (Role Router). Tujuannya adalah untuk menemukan role_id yang paling relevan secara semantik dengan pertanyaan pengguna.

    Tujuan: Menerima embedding pertanyaan pengguna dan mencocokkannya dengan RolesEmbeddings yang tersedia untuk language_code yang diberikan.

    Parameter:

        query_embedding: Vektor pertanyaan pengguna.

        query_language_code: Kode bahasa (misal: 'id') untuk memfilter peran.

        query_default_role_id: Penting: ID peran fallback yang akan dikembalikan jika tidak ada peran yang cocok atau jika language_code tidak valid.

    Logika:

        Validasi Bahasa: Pertama, ia memeriksa apakah ada peran yang terdaftar untuk query_language_code. Jika tidak, ia akan langsung mengembalikan query_default_role_id untuk efisiensi.

        Pencarian Vektor: Ia melakukan pencarian kesamaan kosinus (<=>) terhadap peran yang bahasanya cocok.

        Penanganan Hasil Kosong: Jika pencarian tidak menemukan peran yang melebihi match_threshold, ia akan mengembalikan query_default_role_id (sesuai alur B3 -> B5).

    Hasil: Fungsi ini dijamin selalu mengembalikan satu baris (baik peran yang paling cocok atau peran default).

Kode SQL

SQL

-- PARSE: 01-find-relevant-role-id-v4.sql
CREATE OR REPLACE FUNCTION find_relevant_role_id(
    query_embedding public.app_vector,
    query_language_code VARCHAR(10),
    query_default_role_id UUID,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 1
)
RETURNS TABLE (
    role_id_result UUID,
    similarity_score FLOAT,
    language_code_result VARCHAR(10)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validasi: Periksa apakah ada peran untuk bahasa ini
    IF NOT EXISTS (
        SELECT 1 FROM public."RolesEmbeddings" re 
        WHERE re.language_code = query_language_code
    ) THEN
        -- Bahasa tidak ada, kembalikan default secara paksa
        RETURN QUERY
        SELECT query_default_role_id, 1.0, query_language_code;
        RETURN;
    END IF;

    -- Lakukan pencarian utama
    RETURN QUERY
    SELECT
        re.role_id,
        1 - (re.embedding <=> query_embedding) AS score,
        re.language_code
    FROM
        public."RolesEmbeddings" AS re
    WHERE
        re.language_code = query_language_code
        AND 1 - (re.embedding <=> query_embedding) > match_threshold
    ORDER BY
        score DESC
    LIMIT
        match_count;

    -- Penanganan Hasil Kosong: Tidak ada yang cocok di atas threshold
    IF NOT FOUND THEN
        -- Kembalikan default
        RETURN QUERY
        SELECT query_default_role_id, match_threshold, query_language_code;
    END IF;
END;
$$;