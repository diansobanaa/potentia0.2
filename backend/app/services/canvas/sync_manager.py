# File: backend/services/canvas/sync_manager.py
# (DIREFACTOR - handle_block_mutation sekarang me-return hasil)

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import WebSocket

from app.db.supabase_client import get_supabase_admin_async_client
from app.core.exceptions import DatabaseError, NotFoundError

from app.services.canvas.lexorank_service import LexoRankService #
from app.services.broadcast import broadcast_to_canvas #
from app.db.queries.canvas import block_queries


logger = logging.getLogger(__name__)

class CanvasSyncManager:
    """
    Service untuk mengelola sinkronisasi canvas real-time.
    """
    
    def __init__(self):
        # Service ini tetap memiliki service lain
        self.lexorank_service = LexoRankService()

    
    async def _get_admin_client(self):
        """Helper untuk mendapatkan admin client."""
        return await get_supabase_admin_async_client()

    async def send_initial_state(self, websocket: WebSocket, canvas_id: UUID):
        # (Fungsi ini tidak berubah dari refactor sebelumnya)
        try:
            admin_client = await self._get_admin_client()
            blocks = await block_queries.get_blocks_by_canvas_rpc(admin_client, canvas_id)
            server_seq = await block_queries.get_latest_server_seq_db(admin_client, canvas_id)
            
            await websocket.send_text(json.dumps({
                "type": "initial_state",
                "payload": {"blocks": blocks, "server_seq": server_seq}
            }))
        except (Exception, DatabaseError) as e:
            logger.error(f"Error sending initial state: {e}", exc_info=True)
            await websocket.send_text(json.dumps({
                "type": "error", "message": "Failed to load canvas"
            }))
    
    async def handle_block_mutation(
        self, 
        canvas_id: UUID, 
        user_id: UUID, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Menangani mutasi block dari klien dan MENGEMBALIKAN hasil RPC.
        """
        admin_client = None
        try:
            client_op_id = payload.get("client_op_id")
            block_id_str = payload.get("block_id")
            block_id = UUID(block_id_str) if block_id_str else None
            action = payload.get("action")
            update_data = payload.get("update_data", {})
            expected_version = payload.get("expected_version")
            
            if not client_op_id or not action:
                raise ValueError("Mutasi dibatalkan: client_op_id atau action hilang.")
            
            admin_client = await self._get_admin_client()

            if action == "create" and not block_id:
                block_id = UUID(str(UUID.uuid4()))
            
            if await block_queries.check_duplicate_operation_db(
                admin_client, client_op_id, block_id
            ):
                logger.debug(f"Operasi duplikat diabaikan: {client_op_id}")
                return {"status": "success", "reason": "duplicate_ignored"}
            
            current_block = None
            if block_id and action in ["update", "delete"]:
                current_block = await block_queries.get_block_by_id_rpc(
                    admin_client, block_id
                )
                if not current_block and action == "delete":
                    return {"status": "success", "reason": "already_deleted"}
                
                if current_block and expected_version is not None and \
                   current_block.get("version") != expected_version:
                    
                    return {
                        "status": "conflict",
                        "block_id": str(block_id),
                        "current_version": current_block.get("version"),
                        "current_block": current_block,
                        "client_op_id": client_op_id
                    }
            
            if action == "create" and "y_order" not in update_data:
                parent_id = update_data.get("parent_id")
                parent_id = UUID(parent_id) if parent_id else None
                position = update_data.get("position", "end")
                update_data["y_order"] = await self.lexorank_service.generate_order(
                    canvas_id, parent_id, position
                )
            
            rpc_params = {
                "p_block_id": str(block_id),
                "p_canvas_id": str(canvas_id),
                "p_client_op_id": client_op_id,
                "p_user_id": str(user_id),
                "p_action": action,
                "p_parent_id": str(update_data["parent_id"]) if update_data.get("parent_id") else None,
                "p_y_order": update_data.get("y_order"),
                "p_type": update_data.get("type"),
                "p_content": update_data.get("content"),
                "p_properties": update_data.get("properties"),
                "p_ai_metadata": update_data.get("ai_metadata")
            }
            
            rpc_params = {k: v for k, v in rpc_params.items() if v is not None}

            result = await block_queries.execute_mutation_rpc(admin_client, rpc_params)
            
            return result
                
        except (Exception, DatabaseError) as e:
            logger.error(f"Error handling block mutation: {e}", exc_info=True)
            raise

    async def handle_presence_update(
        self, 
        canvas_id: UUID, 
        user_id: UUID, 
        payload: Dict[str, Any]
    ):
        # (Fungsi ini tidak berubah)
        try:
            await broadcast_to_canvas(canvas_id, {
                "type": "presence",
                "payload": {"user_id": str(user_id), "data": payload}
            }, exclude_user_id=user_id)
        except Exception as e:
            logger.error(f"Error handling presence update: {e}", exc_info=True)
            
    async def broadcast_presence_update(
        self, 
        canvas_id: UUID, 
        user_id: UUID, 
        presence_data: Dict[str, Any]
    ):
        # (Fungsi ini tidak berubah)
        await broadcast_to_canvas(canvas_id, {
            "type": "presence",
            "payload": {"user_id": str(user_id), "data": presence_data}
        })

    async def _send_error_to_user(
        self, 
        canvas_id: UUID, 
        user_id: UUID, 
        error: Any
    ):
        # (Fungsi ini tidak berubah)
        try:
            from app.api.v1.endpoints.socket import active_connections
            if canvas_id in active_connections and user_id in active_connections[canvas_id]:
                websocket = active_connections[canvas_id][user_id]
                error_message = error
                if isinstance(error, dict):
                    error_message = json.dumps(error)
                elif not isinstance(error, str):
                    error_message = str(error)
                
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": error_message
                }))
        except Exception as e:
            logger.error(f"Error sending error to user {user_id}: {e}", exc_info=True)