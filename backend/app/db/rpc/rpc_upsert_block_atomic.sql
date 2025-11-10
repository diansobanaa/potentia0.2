-- File: backend/db/rpc/rpc_upsert_block_atomic.sql
-- (Implementasi RPC v0.4.3 - Tugas 16)

CREATE OR REPLACE FUNCTION public.rpc_upsert_block_atomic(
    p_block_id UUID,
    p_canvas_id UUID,
    p_client_op_id TEXT,
    p_user_id UUID,
    p_action TEXT, -- 'create', 'update', 'delete'
    p_parent_id UUID DEFAULT NULL,
    p_y_order TEXT DEFAULT NULL,
    p_type TEXT DEFAULT NULL,
    p_content TEXT DEFAULT NULL,
    p_properties JSONB DEFAULT NULL,
    p_ai_metadata JSONB DEFAULT NULL,
    p_expected_version INTEGER DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
-- Jalankan sebagai superadmin untuk bisa menulis ke SystemAudit
SECURITY DEFINER
AS $$
DECLARE
  v_current_version INTEGER;
  v_new_version INTEGER;
  v_server_seq BIGINT;
  v_payload JSONB;
  v_affected_rows INTEGER;
BEGIN
  -- 1. Dapatkan Global Sequence (Wajib per Blueprint)
  v_server_seq := nextval('seq_block_events');

  -- 2. Bangun payload untuk logging
  v_payload := jsonb_build_object(
    'parent_id', p_parent_id,
    'y_order', p_y_order,
    'type', p_type,
    'content', p_content,
    'properties', p_properties,
    'ai_metadata', p_ai_metadata,
    'expected_version', p_expected_version
  );

  -- 3. Log Operasi (Status 'pending')
  INSERT INTO public.BlockOperations
    (block_id, canvas_id, client_op_id, user_id, action, server_seq, status, payload)
  VALUES
    (p_block_id, p_canvas_id, p_client_op_id, p_user_id, p_action, v_server_seq, 'pending', v_payload);

  -- 4. Lakukan Mutasi
  IF p_action = 'create' THEN
    INSERT INTO public.Blocks
      (block_id, canvas_id, created_by, updated_by, parent_id, y_order, type, content, properties, version, created_at, updated_at)
    VALUES
      (p_block_id, p_canvas_id, p_user_id, p_user_id, p_parent_id, p_y_order, p_type, p_content, p_properties, 1, NOW(), NOW());
    
    v_new_version := 1;
    v_affected_rows := 1;

  ELSIF p_action = 'update' THEN
    -- Lakukan Optimistic Locking (sesuai blueprint)
    SELECT version INTO v_current_version FROM public.Blocks WHERE block_id = p_block_id FOR UPDATE;

    IF v_current_version IS NULL THEN
      RAISE EXCEPTION 'Block not found: %', p_block_id;
    END IF;

    IF p_expected_version IS NOT NULL AND v_current_version != p_expected_version THEN
      -- Gagal (Konflik)
      UPDATE public.BlockOperations
      SET status = 'conflict', processed_at = NOW(), error_message = 'Version mismatch'
      WHERE client_op_id = p_client_op_id AND block_id = p_block_id;
      
      RETURN jsonb_build_object(
        'status', 'conflict', 
        'server_seq', v_server_seq, 
        'version', v_current_version
      );
    END IF;
    
    v_new_version := v_current_version + 1;

    UPDATE public.Blocks
    SET
      content = COALESCE(p_content, content),
      properties = COALESCE(p_properties, properties),
      ai_metadata = COALESCE(p_ai_metadata, ai_metadata),
      parent_id = COALESCE(p_parent_id, parent_id),
      y_order = COALESCE(p_y_order, y_order),
      version = v_new_version,
      updated_at = NOW(),
      updated_by = p_user_id
    WHERE block_id = p_block_id;
    
    v_affected_rows := 1;

  ELSIF p_action = 'delete' THEN
    -- (Optimistic locking juga bisa diterapkan di sini jika perlu)
    DELETE FROM public.Blocks
    WHERE block_id = p_block_id;
    
    GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
    v_new_version := NULL; -- Tidak ada versi baru

  ELSE
    RAISE EXCEPTION 'Invalid action: %', p_action;
  END IF;

  -- 5. Update Log Operasi (Status 'success')
  UPDATE public.BlockOperations
  SET status = 'success', processed_at = NOW()
  WHERE client_op_id = p_client_op_id AND block_id = p_block_id;

  -- 6. Log Audit (Sesuai Blueprint)
  INSERT INTO public.SystemAudit
    (user_id, action, entity, entity_id, status, server_seq, client_op_id, affected_rows, details)
  VALUES
    (p_user_id, p_action, 'Block', p_block_id, 'success', v_server_seq, p_client_op_id, v_affected_rows, v_payload);

  -- 7. Kembalikan hasil
  RETURN jsonb_build_object(
    'status', 'success', 
    'server_seq', v_server_seq, 
    'version', v_new_version
  );

EXCEPTION
  WHEN OTHERS THEN
    -- 8. Rollback Otomatis & Log Error
    UPDATE public.BlockOperations
    SET status = 'failed', processed_at = NOW(), error_message = SQLERRM
    WHERE client_op_id = p_client_op_id AND block_id = p_block_id;
    
    INSERT INTO public.SystemAudit
      (user_id, action, entity, entity_id, status, server_seq, client_op_id, details)
    VALUES
      (p_user_id, p_action, 'Block', p_block_id, 'failed', v_server_seq, p_client_op_id, 
       jsonb_build_object('error', SQLERRM) || v_payload);
       
    RETURN jsonb_build_object(
      'status', 'failed', 
      'server_seq', v_server_seq, 
      'error', SQLERRM
    );
END;
$$;