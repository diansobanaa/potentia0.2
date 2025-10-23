from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from app.models.block import Block, BlockCreate, BlockUpdate
# PERUBAHAN: Impor dependency 'get_canvas_access'
from app.core.dependencies import get_canvas_access
# PERUBAHAN: Impor semua fungsi query yang akan kita gunakan
from app.db.queries.block_queries import create_block, get_blocks_in_canvas, update_block, delete_block

router = APIRouter()

@router.post("/", response_model=Block, status_code=201)
async def create_new_block(
    canvas_id: UUID,
    block_data: BlockCreate,
    # 'get_canvas_access' sekarang mengembalikan dict
    access_info: dict = Depends(get_canvas_access)
):
    """
    Membuat block baru di dalam canvas tertentu.
    Memerlukan pengguna untuk memiliki akses ke canvas tersebut.
    """
    # Ambil klien yang sudah diautentikasi
    authed_client = access_info["client"]

    # PERUBAHAN: Gunakan .model_dump(mode='json') untuk mengubah
    # UUID/datetime menjadi string yang aman untuk JSON.
    new_block_data = block_data.model_dump(mode='json')
    
    # Teruskan 'authed_client' dan data yang sudah bersih
    new_block = create_block(authed_client, canvas_id, new_block_data)
    
    # PERBAIKAN VALIDASI: Periksa jika new_block adalah None 
    # (misalnya RLS gagal diam-diam)
    if not new_block:
        raise HTTPException(status_code=400, detail="Block creation failed. Check RLS policies or input data.")
        
    return new_block

@router.get("/", response_model=List[Block])
async def list_blocks_in_canvas(
    canvas_id: UUID, 
    # 'get_canvas_access' mengembalikan dict
    access_info: dict = Depends(get_canvas_access)
):
    """
    Menampilkan daftar semua block di dalam canvas tertentu.
    """
    # Ekstrak 'client' dari dict dependency
    authed_client = access_info["client"]
    
    # Teruskan 'authed_client' sebagai argumen pertama
    return get_blocks_in_canvas(authed_client, canvas_id)

@router.patch("/{block_id}", response_model=Block)
async def update_block_content(
    block_id: UUID,
    block_update: BlockUpdate,
    # 'get_canvas_access' mengembalikan dict
    access_info: dict = Depends(get_canvas_access)
):
    """
    Memperbarui konten dari satu block tertentu.
    """
    # Ekstrak 'client' dari dict dependency
    authed_client = access_info["client"]
    
    # PERUBAHAN: Gunakan .model_dump(mode='json')
    update_data = block_update.model_dump(mode='json', exclude_unset=True)
    
    # Teruskan 'authed_client' sebagai argumen pertama
    updated_block = update_block(authed_client, block_id, update_data)
    if not updated_block:
        raise HTTPException(status_code=4.04, detail="Block not found.")
    return updated_block

@router.delete("/{block_id}", status_code=204)
async def delete_a_block(
    block_id: UUID, 
    # 'get_canvas_access' mengembalikan dict
    access_info: dict = Depends(get_canvas_access)
):
    """
    Menghapus satu block tertentu.
    """
    # Ekstrak 'client' dari dict dependency
    authed_client = access_info["client"]
    
    # Teruskan 'authed_client' sebagai argumen pertama
    success = delete_block(authed_client, block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Block not found.")