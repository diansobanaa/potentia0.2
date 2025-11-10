# backend\app\api\v1\endpoints\blocks.py

import logging
from fastapi import APIRouter, Depends, HTTPException, Body, status
from typing import List, Dict, Any, Optional, Annotated 
from uuid import UUID

# Impor model Pydantic
from app.models.block import Block, BlockCreate, BlockUpdate
# Impor dependency untuk otentikasi dan akses
from app.core.dependencies import (
    get_canvas_access, 
    get_embedding_service  
)
# Impor interface service
from app.services.interfaces import IEmbeddingService 
# Impor fungsi query
from app.db.queries.block_queries.create_block_and_embedding import create_block_and_embedding
from app.db.queries.block_queries.update_block_and_embedding import update_block_and_embedding
from app.db.queries.block_queries.delete_block_with_embedding import delete_block_with_embedding
from app.db.queries.block_queries.get_blocks import get_blocks_in_canvas # KITA PERBAIKI AWAIT DI BAWAH

logger = logging.getLogger(__name__)
router = APIRouter(tags=["blocks"])

AuthInfoDep = Annotated[Dict[str, Any], Depends(get_canvas_access)]
EmbeddingServiceDep = Annotated[IEmbeddingService, Depends(get_embedding_service)]

@router.post("/", response_model=Block, status_code=status.HTTP_201_CREATED)
async def create_new_block_endpoint(
    canvas_id: UUID,
    block_data: BlockCreate,
    access_info: AuthInfoDep, 
    embedding_service: EmbeddingServiceDep 
):
    """
    Endpoint untuk membuat block baru. Meneruskan user_id (created_by) untuk audit.
    """
    logger.info(f"Attempting to create block in canvas {canvas_id}")
    authed_client = access_info["client"]
    current_user_id = access_info["user"].id # DITAMBAHKAN: Audit
    new_block_payload = block_data.model_dump(mode='json')
    
    # y_order sudah ditangani default 'a0' di BlockCreate, tidak perlu diubah di sini
    
    try:
        created_block = await create_block_and_embedding(
            authed_client, 
            embedding_service, 
            canvas_id, 
            new_block_payload,
            user_id=current_user_id # DIUBAH: Meneruskan user_id
        )
    except Exception as e:
        logger.error(f"Failed to create block in canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    logger.info(f"Successfully created block {created_block.get('block_id')} in canvas {canvas_id}")
    return created_block

@router.get("/", response_model=List[Block])
async def list_blocks_in_canvas_endpoint(
    canvas_id: UUID,
    access_info: AuthInfoDep 
):
    """Endpoint untuk mengambil semua block dalam sebuah canvas."""
    logger.info(f"Attempting to list blocks for canvas {canvas_id}")
    authed_client = access_info["client"]
    
    # get_blocks_in_canvas sudah async, pastikan di-await
    blocks = await get_blocks_in_canvas(authed_client, canvas_id) # DIUBAH: Menambahkan 'await'
    
    logger.info(f"Found {len(blocks)} blocks for canvas {canvas_id}")
    return blocks

@router.patch("/{block_id}", response_model=Block)
async def update_block_content_endpoint(
    canvas_id: UUID,
    block_id: UUID,
    block_update: BlockUpdate,
    access_info: AuthInfoDep, 
    embedding_service: EmbeddingServiceDep 
):
    """
    Endpoint untuk memperbarui block. Meneruskan user_id (updated_by) untuk audit.
    """
    logger.info(f"Attempting to update block {block_id} in canvas {canvas_id}")
    authed_client = access_info["client"]
    current_user_id = access_info["user"].id # DITAMBAHKAN: Audit
    update_payload = block_update.model_dump(mode='json', exclude_unset=True)

    if not update_payload:
       logger.warning(f"Update requested for block {block_id} with no data.")
       raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")

    try:
        updated_block = await update_block_and_embedding(
            authed_client,
            embedding_service, 
            block_id, 
            update_payload,
            user_id=current_user_id # DIUBAH: Meneruskan user_id
        )
    except Exception as e:
        logger.error(f"Failed to update block {block_id}: {e}", exc_info=True)
        # Mengubah kode status 44 menjadi 404
        if "tidak ditemukan" in str(e): 
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    if updated_block is None:
        logger.error(f"Block {block_id} not found in canvas {canvas_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")

    logger.info(f"Successfully updated block {block_id}")
    return updated_block

@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_block_endpoint(
    canvas_id: UUID,
    block_id: UUID,
    access_info: AuthInfoDep 
):
    """Endpoint untuk menghapus block beserta embeddingnya."""
    logger.info(f"Attempting to delete block {block_id} from canvas {canvas_id}")
    authed_client = access_info["client"]

    success = await delete_block_with_embedding(authed_client, block_id)

    if not success:
       logger.error(f"Block {block_id} not found or failed to delete from canvas {canvas_id}.")
       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found or failed to delete.")

    logger.info(f"Successfully deleted block {block_id}")
    return None