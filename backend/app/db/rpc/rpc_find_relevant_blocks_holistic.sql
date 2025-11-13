-- File: backend/app/db/rpc/rpc_find_relevant_blocks_holistic.sql
-- (File Baru v3.0 - Perbaikan RAG Holistik Goal #2)

DROP FUNCTION IF EXISTS public.rpc_find_relevant_blocks_holistic(
    p_user_id uuid,
    p_query_embedding vector,
    p_query_text tsquery,
    p_limit integer
);

CREATE OR REPLACE FUNCTION public.rpc_find_relevant_blocks_holistic(
    p_user_id uuid,
    p_query_embedding vector,
    p_query_text tsquery,
    p_limit integer DEFAULT 10
)
RETURNS TABLE (
    source_id text,
    content text,
    type text,
    rank real,
    -- [BARU] Provenance (NFR Poin 1)
    metadata jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Ambil semua ID workspace yang bisa diakses pengguna
  CREATE TEMP TABLE IF NOT EXISTS user_workspaces AS
  SELECT wm.workspace_id
  FROM public.workspace_members wm
  WHERE wm.user_id = p_user_id;

  -- Kembalikan hasil RRF (Hybrid Search) dari semua blok yang bisa diakses
  RETURN QUERY
  WITH accessible_blocks AS (
    SELECT 
      b.block_id,
      b.canvas_id,
      b.content,
      b.vector,
      b.type
    FROM 
      public.blocks AS b
    LEFT JOIN 
      public.canvas AS c ON b.canvas_id = c.canvas_id
    LEFT JOIN 
      public.canvas_access AS ca ON b.canvas_id = ca.canvas_id AND ca.user_id = p_user_id
    WHERE
      b.vector IS NOT NULL
      AND (
        c.creator_user_id = p_user_id OR -- 1. Dia pemilik canvas
        ca.user_id = p_user_id OR         -- 2. Dia diundang ke canvas
        c.workspace_id IN (SELECT uw.workspace_id FROM user_workspaces) -- 3. Dia anggota workspace
      )
      -- Filter pencarian (Vektor ATAU Teks)
      AND (
        (b.vector <=> p_query_embedding) < 0.7 
        OR 
        to_tsvector('indonesian', b.content) @@ p_query_text
      )
  )
  -- Hitung RRF Rank (NFR Poin 9)
  SELECT 
    'block_id_' || ab.block_id::text AS source_id,
    ab.content,
    'block'::text AS type,
    (
        (0.6 * (1 - (ab.vector <=> p_query_embedding))) + 
        (0.4 * ts_rank_cd(to_tsvector('indonesian', ab.content), p_query_text))
    )::real AS rank,
    jsonb_build_object(
        'canvas_id', ab.canvas_id,
        'block_type', ab.type
    ) AS metadata
  FROM 
    accessible_blocks AS ab
  ORDER BY 
    rank DESC
  LIMIT 
    p_limit;

  -- Hapus tabel temp
  DROP TABLE user_workspaces;
END;
$$;