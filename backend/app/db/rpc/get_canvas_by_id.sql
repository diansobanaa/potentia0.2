-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.get_canvas_by_id(p_canvas_id uuid);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.get_canvas_by_id(p_canvas_id uuid)
RETURNS TABLE (
    canvas_id uuid,
    workspace_id uuid,
    owner_user_id uuid,
    creator_user_id uuid,
    title text,
    icon text,
    is_archived boolean,
    canvas_metadata jsonb,
    summary_text text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.canvas_id,
    c.workspace_id,
    c.owner_user_id, -- DIUBAH
    c.creator_user_id, -- DIUBAH
    c.title,
    c.icon, -- DIUBAH
    c.is_archived, -- DIUBAH
    c.canvas_metadata, -- DIUBAH
    c.summary_text, -- DIUBAH
    c.created_at,
    c.updated_at
  FROM 
    public.canvas AS c -- DIUBAH
  WHERE 
    c.canvas_id = p_canvas_id;
END;
$$;
