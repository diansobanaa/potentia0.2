-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.find_relevant_conversation_history(
    query_embedding vector,
    match_threshold double precision,
    limit_count integer
);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.find_relevant_conversation_history(
    p_user_id UUID,
    p_query_embedding vector,
    p_match_threshold double precision,
    p_limit_count integer
)
RETURNS TABLE (
    message_id uuid,
    role text,
    content text,
    created_at timestamp with time zone,
    similarity double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.message_id,
    m.role::text,
    m.content,
    m.created_at,
    (1 - (meu.embedding_vector <=> p_query_embedding))::double precision AS similarity
  FROM
    public.messages AS m
  JOIN
    public.message_embedding_user AS meu ON m.message_id = meu.message_id
  WHERE
    m.user_id = p_user_id
    AND (1 - (meu.embedding_vector <=> p_query_embedding)) > p_match_threshold
  ORDER BY
    similarity DESC
  LIMIT
    p_limit_count;
END;
$$;
