-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.find_similar_blocks(
    p_canvas_id uuid,
    p_query_embedding vector,
    p_limit integer
);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.find_similar_blocks(
    p_canvas_id uuid,
    p_query_embedding vector,
    p_limit integer DEFAULT 5
)
RETURNS TABLE (
    block_id uuid,
    canvas_id uuid,
    parent_id uuid,
    y_order text,
    type text,
    content text,
    properties jsonb,
    ai_metadata jsonb,
    version integer,
    created_at timestamp with time zone,
    created_by uuid,
    updated_at timestamp with time zone,
    updated_by uuid,
    vector vector,
    similarity double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    b.block_id,
    b.canvas_id,
    b.parent_id,
    b.y_order,
    b.type,
    b.content,
    b.properties,
    b.ai_metadata,
    b.version,
    b.created_at,
    b.created_by,
    b.updated_at,
    b.updated_by,
    b.vector,
    (1 - (b.vector <=> p_query_embedding))::double precision AS similarity
  FROM 
    public.blocks AS b -- DIUBAH
  WHERE 
    b.canvas_id = p_canvas_id
    AND b.vector IS NOT NULL
  ORDER BY 
    b.vector <=> p_query_embedding
  LIMIT 
    p_limit;
END;
$$;
