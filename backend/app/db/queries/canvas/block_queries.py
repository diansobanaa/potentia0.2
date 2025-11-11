# File: backend/db/queries/canvas/block_queries.py
# (FILE BARU - Ekstraksi dari canvas_sync_manager.py & lexorank.py)

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase.client import AsyncClient
from postgrest import APIResponse
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# --- Diekstrak dari canvas_sync_manager ---

async def get_blocks_by_canvas_rpc(
    admin_client: AsyncClient, 
    canvas_id: UUID, 
    limit: int = 1000, 
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Mengambil daftar block di canvas menggunakan RPC.
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.rpc(
            "get_blocks_by_canvas",
            {
                "p_canvas_id": str(canvas_id),
                "p_limit": limit,
                "p_offset": offset
            }
        ).execute()
        
        # RPC mengembalikan list, jadi response.data adalah list itu sendiri
        return response.data or []
        
    except Exception as e:
        logger.error(f"Error di get_blocks_by_canvas_rpc: {e}", exc_info=True)
        raise DatabaseError("get_blocks_by_canvas_rpc", str(e))

async def get_block_by_id_rpc(
    admin_client: AsyncClient, 
    block_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Mendapatkan data block berdasarkan ID menggunakan RPC.
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.rpc(
            "get_block_by_id",
            {"p_block_id": str(block_id)}
        ).execute()
        
        if response.data:
            return response.data[0]
        return None
        
    except Exception as e:
        logger.error(f"Error di get_block_by_id_rpc: {e}", exc_info=True)
        raise DatabaseError("get_block_by_id_rpc", str(e))

async def get_latest_server_seq_db(
    admin_client: AsyncClient, 
    canvas_id: UUID
) -> int:
    """
    Mendapatkan server_seq terbaru untuk canvas.
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.table("block_operations") \
            .select("server_seq") \
            .eq("canvas_id", str(canvas_id)) \
            .order("server_seq", desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            return response.data[0]["server_seq"]
        return 0
        
    except Exception as e:
        logger.error(f"Error di get_latest_server_seq_db: {e}", exc_info=True)
        raise DatabaseError("get_latest_server_seq_db", str(e))

async def check_duplicate_operation_db(
    admin_client: AsyncClient, 
    client_op_id: str, 
    block_id: UUID
) -> bool:
    """
    Cek apakah operasi sudah pernah dilakukan (idempotency).
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.table("block_operations") \
            .select("op_id", count="exact") \
            .eq("client_op_id", client_op_id) \
            .eq("block_id", str(block_id)) \
            .limit(1) \
            .execute()
            
        return response.count > 0
        
    except Exception as e:
        logger.error(f"Error di check_duplicate_operation_db: {e}", exc_info=True)
        # Gagal mengecek, lebih baik anggap tidak duplikat
        return False

async def execute_mutation_rpc(
    admin_client: AsyncClient, 
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mengeksekusi mutasi block menggunakan RPC rpc_upsert_block_atomic.
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.rpc(
            "rpc_upsert_block_atomic", params
        ).execute()
        
        if response.data:
            return response.data[0]
        
        raise DatabaseError("execute_mutation_rpc", "Tidak ada data dikembalikan dari RPC rpc_upsert_block_atomic.")
        
    except Exception as e:
        logger.error(f"Error di execute_mutation_rpc: {e}", exc_info=True)
        raise DatabaseError("execute_mutation_rpc", str(e))

async def queue_embedding_job_db(
    admin_client: AsyncClient, 
    block_id: UUID, 
    table_name: str
):
    """
    Menambahkan job ke queue untuk proses embedding.
    Sumber:
    """
    try:
        payload = {
            "fk_id": str(block_id),
            "table_destination": table_name,
            "status": "pending"
        }
        response: APIResponse = await admin_client.table("embedding_job_queue") \
            .insert(payload) \
            .execute()
        
        if not response.data:
            raise DatabaseError("queue_embedding_job_db", "Gagal mengantri embedding job.")
            
    except Exception as e:
        logger.error(f"Error di queue_embedding_job_db: {e}", exc_info=True)
        raise DatabaseError("queue_embedding_job_db", str(e))

# --- Diekstrak dari lexorank_service ---

async def get_sibling_blocks_db(
    admin_client: AsyncClient, 
    canvas_id: UUID, 
    parent_id: Optional[UUID]
) -> List[Dict[str, Any]]:
    """
    Mengambil block (hanya id dan y_order) yang se-level (parent_id sama).
    Sumber:
    """
    try:
        query = admin_client.table("blocks") \
            .select("block_id, y_order") \
            .eq("canvas_id", str(canvas_id))
        
        if parent_id:
            query = query.eq("parent_id", str(parent_id))
        else:
            query = query.is_("parent_id", "null")
            
        response: APIResponse = await query.order("y_order").execute()
        return response.data or []
        
    except Exception as e:
        logger.error(f"Error di get_sibling_blocks_db: {e}", exc_info=True)
        raise DatabaseError("get_sibling_blocks_db", str(e))

async def get_all_blocks_for_rebalance_db(
    admin_client: AsyncClient, 
    canvas_id: UUID
) -> List[Dict[str, Any]]:
    """
    Mengambil semua block di canvas untuk di rebalance.
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.table("blocks") \
            .select("block_id, parent_id, y_order") \
            .eq("canvas_id", str(canvas_id)) \
            .order("y_order") \
            .execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error di get_all_blocks_for_rebalance_db: {e}", exc_info=True)
        raise DatabaseError("get_all_blocks_for_rebalance_db", str(e))

async def update_block_y_order_db(
    admin_client: AsyncClient, 
    block_id: UUID, 
    new_y_order: str
):
    """
    Memperbarui y_order dari satu block.
    Sumber:
    """
    try:
        response: APIResponse = await admin_client.table("blocks") \
            .update({"y_order": new_y_order}) \
            .eq("block_id", str(block_id)) \
            .execute()
        
        if not response.data:
            raise NotFoundError("update_block_y_order_db", f"Block {block_id} tidak ditemukan untuk diupdate.")
            
    except Exception as e:
        logger.error(f"Error di update_block_y_order_db: {e}", exc_info=True)
        raise DatabaseError("update_block_y_order_db", str(e))

#--- Diekstrak dari ai_block_manager ---
async def bulk_insert_ai_blocks_rpc(
    admin_client: AsyncClient, 
    canvas_id: UUID,
    creator_id: UUID,
    session_id: UUID,
    blocks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Memanggil RPC 'rpc_bulk_insert_ai_blocks' untuk menyimpan
    semua blok yang dihasilkan AI dalam satu transaksi atomik.
    """
    try:
        params = {
            "p_canvas_id": str(canvas_id),
            "p_creator_id": str(creator_id),
            "p_session_id": str(session_id),
            "p_blocks": json.dumps(blocks) # Kirim sebagai array JSON
        }
        
        response: APIResponse = await admin_client.rpc(
            "rpc_bulk_insert_ai_blocks", params
        ).execute()
        
        if response.data:
            return response.data
        
        raise DatabaseError("bulk_insert_ai_blocks_rpc", "Tidak ada data dikembalikan dari RPC.")
        
    except Exception as e:
        logger.error(f"Error di bulk_insert_ai_blocks_rpc: {e}", exc_info=True)
        raise DatabaseError("bulk_insert_ai_blocks_rpc", str(e))