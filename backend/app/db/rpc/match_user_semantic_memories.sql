-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.match_user_semantic_memories(
    p_user_id uuid,
    query_embedding vector,
    match_threshold double precision,
    match_count integer
);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.match_user_semantic_memories(
    p_user_id uuid,
    query_embedding vector,
    match_threshold double precision DEFAULT 0.5,
    match_count integer DEFAULT 5
)
RETURNS TABLE (
    user_id uuid,
    content text,
    embedding vector,
    similarity double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH similarity_calc AS (
        SELECT DISTINCT ON (m.content)
            m.user_id,
            m.content,
            m.embedding,
            (1 - (m.embedding <=> query_embedding)) AS similarity
        FROM
            public.user_semantic_memories AS m -- DIUBAH
        WHERE
            m.user_id = p_user_id
        ORDER BY
            m.content,
            (1 - (m.embedding <=> query_embedding)) DESC
    )
    SELECT
        sc.user_id,
        sc.content,
        sc.embedding,
        sc.similarity::double precision
    FROM
        similarity_calc AS sc
    WHERE
        sc.similarity > match_threshold
    ORDER BY
        sc.similarity DESC
    LIMIT match_count;
END;
$$;
