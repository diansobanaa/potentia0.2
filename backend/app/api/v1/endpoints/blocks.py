# PARSE: 21-fix-blocks-endpoint-v2.py

import logging
from fastapi import APIRouter, Depends, HTTPException, Body, status
from typing import List, Dict, Any, Optional, Annotated # <-- DIUBAH
from uuid import UUID

# Impor model Pydantic
from app.models.block import Block, BlockCreate, BlockUpdate
# Impor dependency untuk otentikasi dan akses
from app.core.dependencies import (
    get_canvas_access, 
    get_embedding_service  # <-- DIUBAH: Impor factory service
)
# Impor interface service
from app.services.interfaces import IEmbeddingService # <-- DIUBAH
# Impor fungsi query
from app.db.queries.block_queries.create_block_and_embedding import create_block_and_embedding
from app.db.queries.block_queries.update_block_and_embedding import update_block_and_embedding
from app.db.queries.block_queries.delete_block_with_embedding import delete_block_with_embedding
from app.db.queries.block_queries.get_blocks import get_blocks_in_canvas

logger = logging.getLogger(__name__)
router = APIRouter(tags=["blocks"])

# --- DIUBAH: Tipe Alias untuk DI yang bersih ---
AuthInfoDep = Annotated[Dict[str, Any], Depends(get_canvas_access)]
EmbeddingServiceDep = Annotated[IEmbeddingService, Depends(get_embedding_service)]
# ---

@router.post("/", response_model=Block, status_code=status.HTTP_201_CREATED)
async def create_new_block_endpoint(
    canvas_id: UUID,
    block_data: BlockCreate,
    access_info: AuthInfoDep, # <-- DIUBAH
    embedding_service: EmbeddingServiceDep # <-- DIUBAH: Inject service
):
    """
    Endpoint untuk membuat block baru beserta embeddingnya.
    
    INPUT: BlockCreate (type: BlockType, content: str, y_order: float).
    OUTPUT: Block (Block_id, content, y_order, ai_metadata).
    
    KAPAN DIGUNAKAN: Di Canvas Editor saat pengguna menekan Enter (membuat block baru) atau memasukkan konten.
    """
    logger.info(f"Attempting to create block in canvas {canvas_id}")
    authed_client = access_info["client"]
    new_block_payload = block_data.model_dump(mode='json')

    try:
        # --- DIUBAH: Teruskan service ke fungsi query ---
        created_block = await create_block_and_embedding(
            authed_client, 
            embedding_service, 
            canvas_id, 
            new_block_payload
        )
    except Exception as e:
        logger.error(f"Failed to create block in canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    logger.info(f"Successfully created block {created_block.get('block_id')} in canvas {canvas_id}")
    return created_block

@router.get("/", response_model=List[Block])
async def list_blocks_in_canvas_endpoint(
    canvas_id: UUID,
    access_info: AuthInfoDep # <-- DIUBAH (Konsistensi)
):
    """Endpoint untuk mengambil semua block dalam sebuah canvas."""
    logger.info(f"Attempting to list blocks for canvas {canvas_id}")
    authed_client = access_info["client"]
    
    # Fungsi 'get_blocks_in_canvas' Anda juga harus dibuat non-blocking
    # (menggunakan asyncio.to_thread) jika belum.
    blocks = get_blocks_in_canvas(authed_client, canvas_id) 
    
    logger.info(f"Found {len(blocks)} blocks for canvas {canvas_id}")
    return blocks

@router.patch("/{block_id}", response_model=Block)
async def update_block_content_endpoint(
    canvas_id: UUID,
    block_id: UUID,
    block_update: BlockUpdate,
    access_info: AuthInfoDep, # <-- DIUBAH
    embedding_service: EmbeddingServiceDep # <-- DIUBAH: Inject service
):
    """
    Endpoint untuk memperbarui block. Jika konten berubah, embedding juga diperbarui di background.
    
    INPUT: BlockUpdate (content: Optional[str], y_order: Optional[float]).
    OUTPUT: Block (Objek block yang telah diperbarui).
    
    KAPAN DIGUNAKAN: Di Canvas Editor saat pengguna mengetik (throttled save) atau menyeret block (mengubah y_order).
    
    NOTE: KITA BELUM TAHU DATA AKAN DITAMPILKAN SEPERTI APA DALAM CANVAS
    """
    logger.info(f"Attempting to update block {block_id} in canvas {canvas_id}")
    authed_client = access_info["client"]
    update_payload = block_update.model_dump(mode='json', exclude_unset=True)

    if not update_payload:
       logger.warning(f"Update requested for block {block_id} with no data.")
       raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")

    try:
        # --- DIUBAH: Teruskan service ke fungsi query ---
        updated_block = await update_block_and_embedding(
            authed_client,
            embedding_service, # <-- DIUBAH
            block_id, 
            update_payload
        )
    except Exception as e:
        logger.error(f"Failed to update block {block_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    if updated_block is None:
        logger.error(f"Block {block_id} not found in canvas {canvas_id}.")
        raise HTTPException(status_code=status.HTTP_44_NOT_FOUND, detail="Block not found.")

    logger.info(f"Successfully updated block {block_id}")
    return updated_block

@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_block_endpoint(
    canvas_id: UUID,
    block_id: UUID,
    access_info: AuthInfoDep # <-- DIUBAH
):
    """Endpoint untuk menghapus block beserta embeddingnya."""
    logger.info(f"Attempting to delete block {block_id} from canvas {canvas_id}")
    authed_client = access_info["client"]

    # Fungsi ini juga harus dibuat non-blocking (asyncio.to_thread)
    success = await delete_block_with_embedding(authed_client, block_id)

    if not success:
       logger.error(f"Block {block_id} not found or failed to delete from canvas {canvas_id}.")
       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found or failed to delete.")

    logger.info(f"Successfully deleted block {block_id}")
    return None