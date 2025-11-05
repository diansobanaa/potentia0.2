3. Fungsi: find_relevant_history

Deskripsi

Fungsi ini adalah Pencari Memori Percakapan (Conversation Memory Retriever). Tujuannya adalah mengambil pesan-pesan sebelumnya (dari pengguna atau AI) yang relevan dengan pertanyaan baru pengguna.

    Tujuan: Menerima embedding pertanyaan pengguna dan conversation_id yang aktif, lalu mencari Messages yang relevan secara semantik hanya di dalam percakapan tersebut.

    Parameter:

        query_embedding: Vektor pertanyaan pengguna.

        query_conversation_id: UUID dari percakapan yang sedang aktif.

    Logika:

        Validasi Percakapan: Pertama, ia memeriksa apakah query_conversation_id ada di tabel Conversations. Jika tidak, ia akan langsung mengembalikan set kosong.

        Pencarian Vektor: Ia melakukan pencarian kesamaan kosinus terhadap MessageEmbeddings yang difilter berdasarkan conversation_id.

        Join Konten: Ia menggabungkan hasil message_id yang relevan dengan tabel Messages untuk mendapatkan content teks dan role ('user' atau 'ai').

    Hasil: Fungsi ini mengembalikan set kosong (0 baris) jika tidak ada riwayat pesan yang ditemukan atau jika conversation_id tidak valid (sesuai alur B7 -> B9).

Kode SQL

SQL

-- PARSE: 03-find-relevant-history-v4.sql
CREATE OR REPLACE FUNCTION find_relevant_history(
    query_embedding public.app_vector,
    query_conversation_id UUID,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    message_id_result UUID,
    role_result public.message_role,
    content_result TEXT,
    similarity_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validasi: Periksa apakah conversation_id valid
    IF NOT EXISTS (
        SELECT 1 FROM public."Conversations" c 
        WHERE c.conversation_id = query_conversation_id
    ) THEN
        -- Jika conversation_id tidak valid, hentikan dan kembalikan set kosong
        RETURN;
    END IF;

    -- Lakukan pencarian utama jika valid
    RETURN QUERY
    SELECT
        m.message_id AS message_id_result,
        m.role AS role_result,
        m.content AS content_result,
        1 - (me.embedding <=> query_embedding) AS similarity_score
    FROM
        public."MessageEmbeddings" AS me
    JOIN
        public."Messages" AS m ON me.message_id = m.message_id
    WHERE
        me.conversation_id = query_conversation_id
        AND 1 - (me.embedding <=> query_embedding) > match_threshold
    ORDER BY
        similarity_score DESC
    LIMIT
        match_count;

    -- Catatan: Jika tidak ada hasil (NOT FOUND), 
    -- fungsi akan otomatis mengembalikan set kosong. Ini sesuai desain.
END;
$$;