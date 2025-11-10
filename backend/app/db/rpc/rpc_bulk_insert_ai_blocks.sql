CREATE OR REPLACE FUNCTION rpc_bulk_insert_ai_blocks(
    p_canvas_id UUID,
    p_creator_id UUID, -- Ini akan menjadi 'AI_USER_ID'
    p_session_id UUID, -- 'generation_session_id'
    p_blocks JSONB     -- Array JSON [BlockCreatePayload]
) 
RETURNS SETOF "Blocks" AS $$
DECLARE
    v_base_y_order TEXT;
    v_inserted_blocks "Blocks"[];
    v_y_orders TEXT[];
    v_block_count INT;
BEGIN
    -- 1. Dapatkan y_order terakhir (1x Panggilan DB)
    SELECT y_order INTO v_base_y_order FROM "Blocks"
    WHERE canvas_id = p_canvas_id AND parent_id IS NULL
    ORDER BY y_order DESC LIMIT 1;

    -- 2. Dapatkan jumlah blok dari JSON
    SELECT count(*) INTO v_block_count FROM jsonb_array_elements(p_blocks);

    -- 3. Hasilkan y_order baru secara massal (Solusi Bottleneck W2)
    -- Memanggil fungsi yang baru kita buat
    SELECT lexorank_generate(v_base_y_order, NULL, v_block_count)
    INTO v_y_orders;

    -- 4. Bulk Insert (Atomik)
    WITH new_blocks AS (
        SELECT
            gen_random_uuid() AS block_id,
            p_canvas_id,
            p_creator_id AS creator_user_id,
            p_creator_id AS updated_by,
            b.type,
            b.content,
            b.properties,
            v_y_orders[b.row_num] AS y_order, -- Gunakan y_order yang di-batch
            p_session_id AS generation_session_id
        FROM 
            jsonb_to_recordset(p_blocks) 
                AS b(type TEXT, content TEXT, properties JSONB)
            WITH ORDINALITY AS t(b, row_num)
    )
    INSERT INTO "Blocks" (
        block_id, canvas_id, creator_user_id, updated_by, 
        type, content, properties, y_order, generation_session_id,
        -- Set default v0.4.3
        version, created_at, updated_at 
    )
    SELECT 
        block_id, canvas_id, creator_user_id, updated_by,
        type, content, properties, y_order, generation_session_id,
        1, NOW(), NOW() -- Set default
    FROM new_blocks
    RETURNING * INTO v_inserted_blocks; -- Kembalikan blok yang baru dibuat

    -- 5. Audit Batch (Solusi S5)
    INSERT INTO "SystemAudit" (
        user_id, action, entity, entity_id, status, details
    )
    VALUES (
        p_creator_id, 
        'ai_bulk_create', 
        'Canvas', 
        p_canvas_id, 
        'success', 
        jsonb_build_object(
            'block_count', array_length(v_inserted_blocks, 1),
            'generation_session_id', p_session_id
        )
    );

    -- 6. Kembalikan semua blok yang baru dibuat
    RETURN QUERY SELECT * FROM unnest(v_inserted_blocks);

END;
$$ LANGUAGE plpgsql SECURITY DEFINER;