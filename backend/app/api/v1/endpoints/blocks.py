from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from app.models.block import Block, BlockCreate, BlockUpdate
from app.core.dependencies import get_canvas_access
from app.db.queries.block_queries import create_block, get_blocks_in_canvas, update_block, delete_block

router = APIRouter()

@router.post("/", response_model=Block, status_code=201)
async def create_new_block(
    canvas_id: UUID,
    block_data: BlockCreate,
    canvas: dict = Depends(get_canvas_access)
):
    new_block = create_block(canvas_id, block_data.model_dump())
    return new_block

@router.get("/", response_model=List[Block])
async def list_blocks_in_canvas(canvas_id: UUID, canvas: dict = Depends(get_canvas_access)):
    return get_blocks_in_canvas(canvas_id)

@router.patch("/{block_id}", response_model=Block)
async def update_block_content(
    block_id: UUID,
    block_update: BlockUpdate,
    canvas: dict = Depends(get_canvas_access)
):
    updated_block = update_block(block_id, block_update.model_dump(exclude_unset=True))
    if not updated_block:
        raise HTTPException(status_code=404, detail="Block not found.")
    return updated_block

@router.delete("/{block_id}", status_code=204)
async def delete_a_block(block_id: UUID, canvas: dict = Depends(get_canvas_access)):
    success = delete_block(block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Block not found.")