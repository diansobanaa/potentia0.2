-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.get_canvas_with_access(
    p_user_id uuid,
    p_canvas_id uuid
);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.get_canvas_with_access(
    p_user_id uuid,
    p_canvas_id uuid
)
RETURNS TABLE (
    canvas_id uuid,
    workspace_id uuid,
    user_id uuid,
    creator_user_id uuid,
    title text,
    icon text,
    is_archived boolean,
    canvas_metadata jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    summary_text text,
    role text,
    is_owner boolean,
    is_creator boolean
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_canvas RECORD;
    v_user_id TEXT := p_user_id::TEXT;
    v_canvas_id TEXT := p_canvas_id::TEXT;
    v_user_role TEXT := 'viewer';
    v_is_owner BOOLEAN := FALSE;
    v_is_creator BOOLEAN := FALSE;
BEGIN
    SELECT * INTO v_canvas FROM public.canvas WHERE canvas_id = p_canvas_id; -- DIUBAH
    
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    -- (Kolom 'user_id' di 'canvas' sekarang adalah 'owner_user_id')
    IF v_canvas.creator_user_id = v_user_id THEN
        v_is_creator := TRUE;
        v_is_owner := TRUE;
        v_user_role := 'owner';
    END IF;
    
    IF v_canvas.owner_user_id = v_user_id THEN -- DIUBAH
        v_is_owner := TRUE;
        v_user_role := 'owner';
    END IF;
    
    IF v_canvas.workspace_id IS NOT NULL AND NOT v_is_owner THEN
        SELECT role INTO v_user_role FROM public.workspace_members -- DIUBAH
        WHERE workspace_id = v_canvas.workspace_id AND user_id = v_user_id;
        
        IF v_user_role = 'admin' THEN
            v_is_owner := TRUE;
        END IF;
    END IF;
    
    IF NOT v_is_owner THEN
        SELECT role INTO v_user_role FROM public.canvas_access -- DIUBAH
        WHERE canvas_id = v_canvas_id AND user_id = v_user_id;
    END IF;
    
    RETURN QUERY
    SELECT 
        v_canvas.canvas_id,
        v_canvas.workspace_id,
        v_canvas.owner_user_id, -- DIUBAH
        v_canvas.creator_user_id,
        v_canvas.title,
        v_canvas.icon,
        v_canvas.is_archived,
        v_canvas.canvas_metadata,
        v_canvas.created_at,
        v_canvas.updated_at,
        v_canvas.summary_text,
        v_user_role,
        v_is_owner,
        v_is_creator;
END;
$$;
