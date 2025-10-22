import re
from datetime import datetime, timedelta
from uuid import UUID
from app.db.queries.schedule_queries import create_schedule
from app.db.queries.block_queries import create_block
from app.services.audit_service import log_action

def parse_schedule_from_text(text: str) -> Optional[dict]:
    """
    MEMO: Ini adalah implementasi parser yang sangat sederhana untuk MVP.
    - Hanya mengenali kata kunci "besok".
    - Hanya mengenali format "jam X".
    - Tidak robust terhadap variasi bahasa (lusa, hari senin, 14:30, dll).

    REKOMENDASI PERBAIKAN MASA DEPAN:
    Gunakan Gemini Function Calling (Tool Use).
    1. Definisikan 'tool' create_schedule dengan parameter title (str), start_time (datetime), end_time (datetime).
    2. Biarkan AI yang mem-parsing bahasa alami pengguna ("Rapat besok jam 2 siang") dan mengubahnya
       menjadi panggilan fungsi terstruktur. Ini jauh lebih kuat dan fleksibel.
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

async def create_schedule_from_ai(workspace_id: UUID, creator_id: UUID, text: str, canvas_id: UUID):
    schedule_data = parse_schedule_from_text(text)
    if schedule_data:
        schedule_data["workspace_id"] = str(workspace_id)
        schedule_data["creator_user_id"] = str(creator_id)
        
        new_schedule = create_schedule(schedule_data)
        if new_schedule:
            block_content = f"🗓️ **{new_schedule['title']}**\nWaktu: {new_schedule['start_time']} - {new_schedule['end_time']}"
            block_data = {
                "type": "text",
                "content": block_content,
                "properties": {"schedule_id": new_schedule['schedule_id']},
                "y_order": 999.0
            }
            create_block(canvas_id, block_data)
            log_action(creator_id, "schedule.create", {"schedule_id": new_schedule['schedule_id']})
            return new_schedule
    return None