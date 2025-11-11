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
    p_match_threshold double precision DEFAULT 0.7,
    p_match_count integer DEFAULT 5
)
RETURNS TABLE (
    summary_id uuid,
    context_id uuid,
    summary_text text,
    similarity double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.summary_id,
    s.context_id,
    s.summary_text,
    (1 - (e.embedding_vector <-> p_query_embedding))::double precision AS similarity
  FROM
    public.summary_memory_embeddings AS e
  JOIN
    public.summary_memory AS s ON e.summary_id = s.summary_id
  WHERE
    s.user_id = p_user_id
    AND (1 - (e.embedding_vector <-> p_query_embedding)) > p_match_threshold
  ORDER BY
    similarity DESC
  LIMIT
    p_match_count;
END;
$$;
