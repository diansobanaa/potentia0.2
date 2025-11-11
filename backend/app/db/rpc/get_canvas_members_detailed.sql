-- Hapus versi lama (jika ada)
DROP FUNCTION IF EXISTS public.get_canvas_members_detailed(p_canvas_id uuid);

-- Buat versi baru yang distandarisasi
CREATE OR REPLACE FUNCTION public.get_canvas_members_detailed(p_canvas_id uuid)
RETURNS TABLE (
    role text,
    user_details jsonb
)
LANGUAGE sql
AS $$
WITH canvas_info AS (
  SELECT 
    c.creator_user_id, 
    c.workspace_id
  FROM public.canvas c -- DIUBAH
  WHERE c.canvas_id = p_canvas_id
),
all_sources AS (
  -- Sumber 1: Owner/Creator (Prioritas 1)
  SELECT 
    c.creator_user_id AS user_id,
    'owner' AS role,
    1 AS priority
  FROM canvas_info c

  UNION ALL

  -- Sumber 2: Anggota yang di-invite (CanvasAccess) (Prioritas 2)
  SELECT 
    ca.user_id,
    ca.role::text,
    2 AS priority
  FROM public.canvas_access ca -- DIUBAH
  WHERE ca.canvas_id = p_canvas_id

  UNION ALL

  -- Sumber 3: Anggota Workspace (Prioritas 3)
  SELECT 
    wm.user_id,
    wm.role::text,
    3 AS priority
  FROM public.workspace_members wm -- DIUBAH
  JOIN canvas_info c ON wm.workspace_id = c.workspace_id
)
SELECT
  a.role,
  jsonb_build_object(
    'user_id', u.user_id,
    'name', u.name,
    'email', u.email
  ) AS user_details
FROM (
  SELECT DISTINCT ON (user_id)
    user_id,
    role
  FROM all_sources
  ORDER BY
    user_id, 
    priority ASC
) a
JOIN public.users u ON a.user_id = u.user_id; -- DIUBAH
$$;
