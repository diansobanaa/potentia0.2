from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.notification_service import send_notification_to_user

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

@router.get("/stream")
async def notifications_stream(request: Request, current_user: User = Depends(get_current_user)):
    """
    Endpoint untuk koneksi Server-Sent Events.
    Frontend akan menghubung ke endpoint ini.
    """
    async def event_stream():
        async with EventSourceResponse() as event_source:
            # Simpan koneksi saat dibuat
            active_sse_connections[current_user.id] = event_source
            try:
                # Jaga koneksi tetap terbuka
                while True:
                    await asyncio.sleep(10) # Biar idle jika tidak ada pesan
            except asyncio.CancelledError:
                # Koneksi ditutup oleh client
                break
            finally:
                # Hapus koneksi saat selesai
                if current_user.id in active_sse_connections:
                    del active_sponses[current_user.id]
    
    return StreamingResponse(
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Allow-Origin": "*"
        },
        content=event_stream(event_stream)
    )