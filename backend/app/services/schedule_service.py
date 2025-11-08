# File: backend/app/services/schedule_service.py
# (Diperbarui untuk AsyncClient native)

import re
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional, List, Dict, Any
# --- PERBAIKAN: Impor kueri async ---
from app.db.queries.schedule_queries import create_schedule_legacy
from app.db.queries.block_queries.create_block_and_embedding import create_block_and_embedding
# -----------------------------------
from app.services.audit_service import log_action
# --- PERBAIKAN: Impor AsyncClient dan EmbeddingService ---
from supabase.client import AsyncClient
from app.services.interfaces import IEmbeddingService
# -----------------------------------------------------

def parse_schedule_from_text(text: str) -> Optional[dict]:
    """
    (Fungsi helper ini tidak melakukan I/O, jadi tidak perlu diubah)
    """
    if "besok" in text.lower():
        date = datetime.now() + timedelta(days=1)
    else:
        return None
    
    match = re.search(r'jam (\d{1,2})', text.lower())
    if match:
        hour = int(match.group(1))
        start_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        return {
            "title": f"Meeting dari AI: {text[:30]}...",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    return None

async def create_schedule_from_ai(
    # --- PERBAIKAN: Tambahkan dependensi AsyncClient & EmbeddingService ---
    authed_client: AsyncClient,
    embedding_service: IEmbeddingService,
    # -----------------------------------
    workspace_id: UUID, 
    creator_id: UUID, 
    text: str, 
    canvas_id: UUID
):
    """
    (Async Native) Membuat jadwal (versi lama) dari teks AI.
    """
    schedule_data = parse_schedule_from_text(text)
    if schedule_data:
        schedule_data["workspace_id"] = str(workspace_id)
        schedule_data["creator_user_id"] = str(creator_id)
        
        # --- PERBAIKAN: Gunakan 'await' pada kueri async ---
        new_schedule = await create_schedule_legacy(authed_client, schedule_data)
        
        if new_schedule:
            block_content = f"🗓️ **{new_schedule['title']}**\nWaktu: {new_schedule['start_time']} - {new_schedule['end_time']}"
            block_data = {
                "type": "text",
                "content": block_content,
                "properties": {"schedule_id": new_schedule['schedule_id']},
                "y_order": 999.0
            }
            # 'create_block_and_embedding' sudah async
            await create_block_and_embedding(
                authed_client, 
                embedding_service, 
                canvas_id, 
                block_data
            )
            # 'log_action' sudah async
            await log_action(creator_id, "schedule.create", {"schedule_id": new_schedule['schedule_id']})
            return new_schedule
    return None