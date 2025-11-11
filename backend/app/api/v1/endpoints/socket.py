# File: backend/app/api/v1/endpoints/socket.py
# (DIREFACTOR untuk Redis Pub/Sub)

import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.core.dependencies import get_current_user_and_client
from app.models.user import User
from app.db.supabase_client import get_supabase_admin_async_client
from app.services.canvas.sync_manager import CanvasSyncManager
from app.services.canvas.lexorank_service import LexoRankService
from app.services.redis_rate_limiter import rate_limiter #
from app.services.redis_pubsub import redis_pubsub_manager
from app.core.exceptions import DatabaseError
from app.db.queries.canvas import block_queries

logger = logging.getLogger(__name__)
router = APIRouter()

# -----------------------------------------------------------------
# !! PENTING !!
# 'active_connections' sekarang LOKAL untuk worker ini.
# Format: {canvas_id: {user_id: WebSocket}}
# Ini HANYA melacak socket yang dikelola oleh proses worker ini.
# -----------------------------------------------------------------
active_connections: Dict[UUID, Dict[UUID, WebSocket]] = {}

# Instance dari CanvasSyncManager
canvas_sync_manager = CanvasSyncManager() #

# get_current_user_ws (Tidak berubah dari file Anda)
async def get_current_user_ws(websocket: WebSocket, token: str = None) -> User:
    # ... (Implementasi sama persis dengan file socket.py)
    pass 

async def _validate_canvas_access(canvas_id: UUID, user: User) -> bool:
    """Helper untuk memvalidasi akses canvas (logika dari file asli)"""
    try:
        admin_client = await get_supabase_admin_async_client()
        canvas_response = await admin_client.rpc(
            "get_canvas_by_id",
            {"p_canvas_id": str(canvas_id)}
        ).execute()
        
        if not canvas_response.data:
            return False
        
        canvas = canvas_response.data[0]
        user_id = str(user.id)
        
        if canvas.get("owner_id") == user_id:
            return True
        # TODO: Tambahkan cek akses lain (workspace, CanvasAccess)
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking canvas access: {e}")
        return False

async def _pubsub_listener(websocket: WebSocket, canvas_id: UUID, user_id: UUID):
    # (Fungsi ini tidak berubah dari refactor sebelumnya)
    channel = f"canvas:{str(canvas_id)}"
    try:
        async for message in redis_pubsub_manager.subscribe(channel):
            exclude_user_id = message.pop("_exclude_user_id", None)
            if exclude_user_id and str(user_id) == exclude_user_id:
                continue
            await websocket.send_text(json.dumps(message))
    except WebSocketDisconnect:
        logger.info(f"PubSub listener: WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Error di PubSub listener: {e}", exc_info=True)
        
async def _client_listener(websocket: WebSocket, canvas_id: UUID, user: User):
    """
    Tugas yang mendengarkan pesan dari Klien WebSocket.
    (DIREFACTOR untuk menangani return value)
    """
    user_id = user.id
    try:
        while True:
            if not await rate_limiter.check_user_limit(user_id, limit=10, window_seconds=60):
                await websocket.send_text(json.dumps({"type": "error", "message": "Rate limit exceeded"}))
                continue
                
            data = await websocket.receive_text()
            message = json.loads(data)
            
            payload = message.get("payload", {})
            
            if message.get("type") == "mutation":
                # [REFACTOR] Tangani return value dari service
                try:
                    result = await canvas_sync_manager.handle_block_mutation(
                        canvas_id, user_id, payload
                    )
                    
                    if result.get("status") == "success":
                        # Jika sukses, WebSocket bertanggung jawab untuk broadcast
                        block_id = UUID(payload.get("block_id") or result.get("block_id"))
                        action = payload.get("action")
                        
                        block = None
                        if action != "delete":
                            admin_client = await get_supabase_admin_async_client()
                            block = await block_queries.get_block_by_id_rpc(admin_client, block_id)

                        await broadcast_to_canvas(canvas_id, {
                            "type": "mutation",
                            "payload": {
                                "action": action,
                                "block_id": str(block_id),
                                "block": block,
                                "server_seq": result.get("server_seq"),
                                "client_op_id": payload.get("client_op_id")
                            }
                        })
                        
                        # Antrikan job (logika dipindahkan dari manager)
                        if action in ["create", "update"] and "content" in payload.get("update_data", {}):
                            admin_client = await get_supabase_admin_async_client()
                            await block_queries.queue_embedding_job_db(admin_client, block_id, "blocks")
                        
                        if action in ["create", "update"] and "y_order" in payload.get("update_data", {}):
                            await lexorank_service.check_rebalance_needed(canvas_id)
                    
                    elif result.get("status") == "conflict":
                        # Kirim error konflik HANYA ke user ini
                        await canvas_sync_manager._send_error_to_user(
                            canvas_id, user_id, result
                        )
                    
                    # (Status 'duplicate_ignored' tidak perlu melakukan apa-apa)

                except Exception as e:
                    # Tangani error dari service
                    logger.error(f"Gagal memproses mutasi: {e}", exc_info=True)
                    await canvas_sync_manager._send_error_to_user(
                        canvas_id, user_id, f"Error: {e}"
                    )
            
            elif message.get("type") == "presence":
                await canvas_sync_manager.handle_presence_update(
                    canvas_id, user_id, payload
                )
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        logger.info(f"Client listener: WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Error di client listener: {e}", exc_info=True)

router.websocket("/ws/canvas/{canvas_id}")
async def websocket_canvas_sync(
    websocket: WebSocket,
    canvas_id: UUID,
    token: str = None
):
    await websocket.accept()
    
    current_user = await get_current_user_ws(websocket, token)
    if not current_user:
        return #
    
    has_access = await _validate_canvas_access(canvas_id, current_user)
    if not has_access:
        await websocket.close(code=1008, reason="Access denied or canvas not found")
        return

    if canvas_id not in active_connections:
        active_connections[canvas_id] = {}
    active_connections[canvas_id][current_user.id] = websocket
    
    await rate_limiter.add_active_user(current_user.id, canvas_id)
    
    try:
        await canvas_sync_manager.send_initial_state(websocket, canvas_id)

        pubsub_task = asyncio.create_task(
            _pubsub_listener(websocket, canvas_id, current_user.id)
        )
        # [PERBAIKAN] Kirim objek User lengkap
        client_task = asyncio.create_task(
            _client_listener(websocket, canvas_id, current_user) 
        )
        
        done, pending = await asyncio.wait(
            [pubsub_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        for task in pending:
            task.cancel()

    except Exception as e:
        logger.error(f"Error tak terduga di WebSocket handler: {e}", exc_info=True)
    finally:
        # (Blok finally tidak berubah)
        if canvas_id in active_connections and current_user.id in active_connections[canvas_id]:
            del active_connections[canvas_id][current_user.id]
        await rate_limiter.remove_active_user(current_user.id, canvas_id)
        await canvas_sync_manager.broadcast_presence_update(
            canvas_id, current_user.id, {"status": "offline"}
        )
        logger.info(f"User {current_user.id} disconnected from canvas {canvas_id}")
        try:
            await websocket.close()
        except:
            pass