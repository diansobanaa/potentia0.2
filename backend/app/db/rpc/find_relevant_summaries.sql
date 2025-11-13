-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.find_relevant_summaries(
    p_user_id uuid,
    p_query_embedding vector,
    p_match_threshold double precision,
    p_match_count integer
);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.find_relevant_summaries(
    p_user_id uuid,
    p_query_embedding vector,
    p_query_text tsquery, -- [BARU] Untuk Hybrid Search
    p_match_threshold double precision DEFAULT 0.5, -- (Diturunkan untuk RRF)
    p_match_count integer DEFAULT 10 -- (Dinaikkan untuk RRF)
)
RETURNS TABLE (
    summary_id uuid,
    context_id uuid,
    summary_text text,
    similarity double precision,
    rank real -- [BARU]
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.summary_id,
    s.context_id,
    s.summary_text,
    (1 - (e.embedding_vector <-> p_query_embedding))::double precision AS similarity,
    -- [BARU] Hitung rank (RRF) - 0.6 Vektor, 0.4 Teks
    (
        (0.6 * (1 - (e.embedding_vector <-> p_query_embedding))) +
        (0.4 * ts_rank_cd(to_tsvector('indonesian', s.summary_text), p_query_text))
    )::real AS rank
  FROM
    public.summary_memory_embeddings AS e
  JOIN
    public.summary_memory AS s ON e.summary_id = s.summary_id
  WHERE
    s.user_id = p_user_id
    -- [BARU] Gabungkan pencarian (Vektor ATAU Teks)
    AND (
        (1 - (e.embedding_vector <-> p_query_embedding)) > p_match_threshold
        OR
        to_tsvector('indonesian', s.summary_text) @@ p_query_text
    )
  ORDER BY
    rank DESC -- Urutkan berdasarkan rank RRF
  LIMIT
    p_match_count;
END;
$$;