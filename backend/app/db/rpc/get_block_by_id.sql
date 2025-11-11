-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.get_block_by_id(p_block_id uuid);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.get_block_by_id(p_block_id uuid)
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
    vector vector
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
    b.vector
  FROM 
    public.blocks AS b -- DIUBAH
  WHERE 
    b.block_id = p_block_id;
END;
$$;
