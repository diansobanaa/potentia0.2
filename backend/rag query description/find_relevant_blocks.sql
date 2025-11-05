2. Fungsi: find_relevant_blocks

Deskripsi

Fungsi ini adalah Pencari Konteks Canvas (Canvas Context Retriever). Tujuannya adalah mengambil potongan konten (Blocks) yang relevan dari canvas spesifik yang sedang dilihat pengguna.

    Tujuan: Menerima embedding pertanyaan pengguna dan canvas_id yang aktif, lalu mencari Blocks yang relevan secara semantik hanya di dalam canvas tersebut.

    Parameter:

        query_embedding: Vektor pertanyaan pengguna.

        query_canvas_id: UUID dari canvas yang sedang aktif.

    Logika:

        Validasi Canvas: Pertama, ia memeriksa apakah query_canvas_id ada di tabel Canvas. Jika tidak, ia akan langsung mengembalikan set kosong untuk menghemat sumber daya.

        Pencarian Vektor: Ia melakukan pencarian kesamaan kosinus terhadap BlocksEmbeddings yang difilter berdasarkan canvas_id.

        Join Konten: Ia menggabungkan hasil block_id yang relevan dengan tabel Blocks untuk mendapatkan content teks yang sebenarnya.

    Hasil: Fungsi ini mengembalikan set kosong (0 baris) jika tidak ada blok yang ditemukan atau jika canvas_id tidak valid (sesuai alur B11 -> B13). Lapisan aplikasi (Python) bertanggung jawab untuk menangani set kosong ini.

Kode SQL

SQL

-- PARSE: 02-find-relevant-blocks-v4.sql
CREATE OR REPLACE FUNCTION find_relevant_blocks(
    query_embedding public.app_vector,
    query_canvas_id UUID,
    match_threshold FLOAT DEFAULT 0.75,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    block_id_result UUID,
    content_result TEXT,
    similarity_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validasi: Periksa apakah canvas_id valid
    IF NOT EXISTS (SELECT 1 FROM public."Canvas" c WHERE c.canvas_id = query_canvas_id) THEN
        -- Jika canvas_id tidak valid, hentikan dan kembalikan set kosong
        RETURN;
    END IF;

    -- Lakukan pencarian utama jika valid
    RETURN QUERY
    SELECT
        b.block_id AS block_id_result,
        b.content AS content_result,
        1 - (be.embedding <=> query_embedding) AS similarity_score
    FROM
        public."BlocksEmbeddings" AS be
    JOIN
        public."Blocks" AS b ON be.block_id = b.block_id
    WHERE
        be.canvas_id = query_canvas_id
        AND b.canvas_id = query_canvas_id -- Validasi konsistensi data
        AND 1 - (be.embedding <=> query_embedding) > match_threshold
    ORDER BY
        similarity_score DESC
    LIMIT
        match_count;
    
    -- Catatan: Jika tidak ada hasil (NOT FOUND), 
    -- fungsi akan otomatis mengembalikan set kosong. Ini sesuai desain.
END;
$$;