# File: backend/app/core/dependencies.py
# (Diperbarui untuk AsyncClient dan validasi token yang aman)

import logging
import asyncio
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
from typing import Union, Dict, Any, Annotated, List, Tuple, Optional
from fastapi import Path
from supabase.client import AsyncClient, create_async_client
from postgrest.exceptions import APIError
import httpx

from app.core.config import settings #
from app.core.exceptions import DatabaseError, NotFoundError, PermissionError
from app.db.supabase_client import get_supabase_admin_async_client
from app.models.user import User, SubscriptionTier
from app.models.workspace import MemberRole
from app.models.canvas import CanvasRole
from app.models.schedule import CalendarVisibility, SubscriptionRole, Schedule, RsvpStatus, GuestRole
from langchain_core.runnables import Runnable

# --- Impor Database Queries ---
# (Struktur query yang baru)
from app.db.queries.canvas import canvas_queries, canvas_member_queries
from app.db.queries.workspace import workspace_queries
from app.db.queries.calendar import calendar_queries


# --- Impor Service ---
from app.services.interfaces import IEmbeddingService
from app.services.embedding_service import GeminiEmbeddingService #
from app.services.chat_engine.judge_chain import get_judge_chain
from app.services.conversations_list_service import ConversationListService
from app.services.conversation_messages_service import ConversationMessagesService
from app.services.title_stream_service import TitleStreamService
from app.services.user.user_service import UserService
from app.services.workspace.workspace_service import WorkspaceService
from app.services.calendar.freebusy_service import FreeBusyService
from app.services.calendar.calendar_service import CalendarService
from app.services.calendar.schedule_service import ScheduleService
from app.services.calendar.subscription_service import SubscriptionService
from app.services.calendar.guest_service import GuestService
from app.services.calendar.view_service import ViewService

# --- [REFACTOR] Impor Service Canvas dari lokasi baru ---
from app.services.canvas.list_service import CanvasListService
from app.services.canvas.sync_manager import CanvasSyncManager
from app.services.canvas.lexorank_service import LexoRankService

# --- Konfigurasi Awal ---
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

# Klien sinkron HANYA untuk validasi token (dijalankan di thread)
validation_client = httpx.Client(
    base_url=f"{settings.SUPABASE_URL}/auth/v1",
    headers={"apikey": settings.SUPABASE_ANON_KEY}
)

# Klien Anonim Asinkron (Singleton)
supabase_anon_client: Optional[AsyncClient] = None

async def get_anon_async_client() -> AsyncClient:
    """Membuat singleton untuk klien anonim asinkron."""
    global supabase_anon_client
    if supabase_anon_client is None:
         supabase_anon_client = await create_async_client(
             settings.SUPABASE_URL, 
             settings.SUPABASE_ANON_KEY
         )
    return supabase_anon_client

# --- Representasi Pengguna Tamu ---
class GuestUser:
    id: Union[UUID, None] = None
    is_guest: bool = True
    subscription_tier: SubscriptionTier = SubscriptionTier.user
    def __init__(self, client: AsyncClient):
        self.client = client

# =======================================================================
# === FUNGSI DEPENDENSI (Diperbarui untuk Async) ===
# =======================================================================

async def get_current_user_and_client(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    token = credentials.credentials
    user_id: Optional[str] = None
    user_response_json: Optional[dict] = None 
    
    try:
        def sync_validate_token():
            headers = {"Authorization": f"Bearer {token}"}
            response = validation_client.get("/user", headers=headers)
            response.raise_for_status()
            return response.json()

        user_response_json = await asyncio.to_thread(sync_validate_token)
        
        user_id = user_response_json.get("id")
        if not user_id:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token data")
        logger.debug(f"Token valid untuk user_id: {user_id}")
        
    except httpx.HTTPStatusError as e:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate token: {str(e)}")
        
    try:
        # --- PERBAIKAN: 'await' create_async_client ---
        authed_client: AsyncClient = await create_async_client(
            supabase_url=settings.SUPABASE_URL, 
            supabase_key=settings.SUPABASE_ANON_KEY
        )
        # ---------------------------------------------
        
        await authed_client.auth.set_session(access_token=token, refresh_token="dummy_refresh_token")

        profile_response = await authed_client.table("Users") \
            .select("*") \
            .eq("user_id", user_id) \
            .single() \
            .execute()
            
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User profile not found in internal database.")
            
        profile_data = profile_response.data
        user_model = User.model_validate(profile_data)
        
        logger.debug("Otentikasi async dan pengambilan profil berhasil.")
        return {"user": user_model, "client": authed_client}
        
    except Exception as e:
        logger.error(f"Error setelah validasi token (saat ambil profil/buat klien): {e}", exc_info=True)
        # Tangani error jika 'await' gagal
        if isinstance(e, (APIError, httpx.HTTPError)):
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error after auth: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error after auth: {str(e)}")

async def get_current_user(auth_info: dict = Depends(get_current_user_and_client)) -> User:
    return auth_info["user"]

async def get_current_user_or_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    # --- PERBAIKAN: 'await' klien anonim ---
    anon_client = await get_anon_async_client()
         
    if credentials:
        try:
            return await get_current_user_and_client(credentials)
        except HTTPException:
            # --- PERBAIKAN: Pass klien ke GuestUser ---
            return {"user": GuestUser(client=anon_client), "client": anon_client}
    else:
        # --- PERBAIKAN: Pass klien ke GuestUser ---
        return {"user": GuestUser(client=anon_client), "client": anon_client}
    
# (Tier/Role checks tidak berubah)
async def get_user_tier(current_user: User = Depends(get_current_user)) -> SubscriptionTier:
    return current_user.subscription_tier
async def require_pro_user(tier: SubscriptionTier = Depends(get_user_tier)):
    if tier not in [SubscriptionTier.pro, SubscriptionTier.admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pro subscription required.")
    return tier
async def require_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.subscription_tier != SubscriptionTier.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user

# --- [PERBAIKAN #5] Semua dependency keamanan sekarang 'async' native ---

async def get_current_workspace_member( 
    workspace_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client)
):
    current_user: User = auth_info["user"]
    authed_client: AsyncClient = auth_info["client"]
    # [REFACTOR] Menggunakan fungsi query
    membership = await workspace_queries.check_user_membership(
        authed_client, workspace_id, current_user.id
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace.")
    return {
        "membership": membership, 
        "user": current_user, 
        "client": authed_client,
        "role": membership.get("role", MemberRole.guest.value)
    }

async def get_workspace_admin_access(
    access_info: Dict[str, Any] = Depends(get_current_workspace_member)
) -> Dict[str, Any]:
    # (Logika tidak berubah, 'get_current_workspace_member' sudah async)
    user_role = access_info.get("role")
    
    if user_role != MemberRole.admin.value:
        # ... (logika error)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an admin of this workspace to perform this action."
        )
    return access_info

async def get_canvas_access( 
    canvas_id: UUID,
    auth_info: dict = Depends(get_current_user_or_guest)
) -> Dict[str, Any]:
    """
    [PERBAIKAN] Blok try/except sekarang menangkap
    NotFoundError dan PermissionError.
    """
    service = CanvasListService(auth_info)
    
    try:
        access_info = await service.get_canvas_with_access(canvas_id)
        access_info["client"] = auth_info["client"]
        access_info["user"] = auth_info["user"]
        return access_info
        
    except NotFoundError as e: # <-- SEKARANG TERDEFINISI
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e: # <-- SEKARANG TERDEFINISI
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def get_canvas_admin_access(
    access_info: Dict[str, Any] = Depends(get_canvas_access)
) -> Dict[str, Any]:
    user_role = access_info.get("role")
    # Role 'owner' atau 'admin' (dari workspace)
    admin_roles = ["owner", "admin", MemberRole.admin.value] 
    if user_role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses admin ke canvas ini diperlukan."
        )
    return access_info

async def get_guest_access(
    schedule_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client) 
) -> Dict[str, Any]:
    current_user: User = auth_info["user"]
    authed_client: AsyncClient = auth_info["client"]
    try:
        response: APIResponse = await authed_client.table("schedule_guests") \
            .select("*") \
            .eq("schedule_id", str(schedule_id)) \
            .eq("user_id", str(current_user.id)) \
            .eq("response_status", RsvpStatus.pending.value)\
            .maybe_single() \
            .execute()
        guest_data = response.data if response.data else None
        if not guest_data:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anda tidak diundang ke acara ini atau sudah merespons.")
        return {"guest": guest_data, "user": current_user, "client": authed_client}
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail="Gagal memvalidasi akses tamu.")
    
async def get_calendar_access(
    calendar_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client)
) -> Dict[str, Any]:
    current_user: User = auth_info["user"]
    authed_client: AsyncClient = auth_info["client"]
    calendar = await get_calendar_by_id(authed_client, calendar_id)
    if not calendar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found.")
    access_info = {"calendar": calendar, "user": current_user, "client": authed_client}
    
    if calendar.get("owner_user_id") and str(calendar["owner_user_id"]) == str(current_user.id):
        access_info["role"] = SubscriptionRole.owner
        return access_info
    if calendar.get("visibility") == CalendarVisibility.public.value:
        access_info["role"] = SubscriptionRole.viewer
        return access_info
    workspace_id_str = calendar.get("workspace_id")
    if workspace_id_str:
        membership = await check_user_membership(authed_client, UUID(workspace_id_str), current_user.id)
        if membership:
             ws_role = membership.get("role", MemberRole.guest.value)
             access_info["role"] = SubscriptionRole.editor if ws_role == MemberRole.admin.value else SubscriptionRole.viewer
             return access_info
    subscription = await get_user_subscription(authed_client, current_user.id, calendar_id)
    if subscription:
        sub_role = subscription.get("role", SubscriptionRole.viewer.value)
        access_info["role"] = sub_role
        return access_info
    raise HTTPException(status_code=403, detail="Access denied to this calendar.")

async def get_calendar_editor_access(
    access_info: Dict[str, Any] = Depends(get_calendar_access)
) -> Dict[str, Any]:
    # (Logika tidak berubah)
    user_role = access_info.get("role")
    admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value] 
    if user_role not in admin_roles:
        raise HTTPException(...)
    return access_info

async def get_schedule_access(
    schedule_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client) 
) -> Dict[str, Any]:
    authed_client: AsyncClient = auth_info["client"]
    schedule = await get_schedule_by_id(authed_client, schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    calendar_id = schedule.get("calendar_id")
    if not calendar_id:
         raise HTTPException(status_code=500, detail="Integritas data error: Acara tidak memiliki kalender.")
    try:
        calendar_access_info = await get_calendar_access(
            UUID(calendar_id), auth_info
        )
        access_info = {"schedule": schedule, **calendar_access_info}
        return access_info
    except HTTPException as e:
        raise e

async def get_subscription_delete_access(
    subscription_id: UUID = Path(..., description="ID langganan yang akan dihapus"),
    auth_info: dict = Depends(get_current_user_and_client)
) -> Dict[str, Any]:
    current_user: User = auth_info["user"]
    authed_client: AsyncClient = auth_info["client"]
    subscription = await get_subscription_by_id(authed_client, subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Langganan (subscription) tidak ditemukan.")
    if str(subscription.get("user_id")) == str(current_user.id):
        return {"subscription": subscription, "user": current_user, "client": authed_client}
    calendar_id = subscription.get("calendar_id")
    if not calendar_id:
         raise HTTPException(status_code=500, detail="Integritas data error: Langganan tidak memiliki kalender.")
    try:
        calendar_access_info = await get_calendar_access(
            UUID(calendar_id), auth_info
        )
        user_role_in_calendar = calendar_access_info.get("role")
        admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value]
        if user_role_in_calendar in admin_roles:
            return {"subscription": subscription, "user": current_user, "client": authed_client}
    except HTTPException:
        pass 
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Anda tidak memiliki izin untuk menghapus anggota ini."
    )
# --- Injeksi Service (Tidak Berubah) ---
embedding_service_instance = GeminiEmbeddingService()
async def get_embedding_service() -> IEmbeddingService:
    yield embedding_service_instance

judge_chain_instance: Optional[Runnable] = None
def get_judge_chain_singleton() -> Runnable:
    global judge_chain_instance
    if judge_chain_instance is None:
        logger.info("Menginisialisasi Judge Chain Singleton...")
        judge_chain_instance = get_judge_chain() 
    yield judge_chain_instance
    
async def get_conversation_list_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client), 
) -> ConversationListService:
    return ConversationListService(auth_info=auth_info)

async def get_conversation_messages_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> ConversationMessagesService:
    return ConversationMessagesService(auth_info=auth_info)

async def get_streaming_title_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> TitleStreamService:
    return TitleStreamService(auth_info=auth_info)

async def get_canvas_list_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> CanvasListService:
    return CanvasListService(auth_info=auth_info)

# [BARU] Injeksi untuk CanvasSyncManager
canvas_sync_manager_instance = CanvasSyncManager()
async def get_canvas_sync_manager() -> CanvasSyncManager:
    return canvas_sync_manager_instance

async def get_user_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> UserService:
    user = auth_info["user"]
    client: AsyncClient = auth_info["client"]
    admin_async_client = await get_supabase_admin_async_client() 
    return UserService(authed_client=client, user=user, admin_client=admin_async_client)

async def get_workspace_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> WorkspaceService:
    user = auth_info["user"]
    client = auth_info["client"]
    return WorkspaceService(authed_client=client, user=user)

async def get_freebusy_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> FreeBusyService:
    return FreeBusyService(auth_info=auth_info)

async def get_calendar_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> CalendarService:
    return CalendarService(auth_info=auth_info)

async def get_schedule_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> ScheduleService:
    return ScheduleService(auth_info=auth_info)

async def get_subscription_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> SubscriptionService:
    return SubscriptionService(auth_info=auth_info)

async def get_guest_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> GuestService:
    return GuestService(auth_info=auth_info)

async def get_view_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> ViewService:
    return ViewService(auth_info=auth_info)

canvas_sync_manager_instance = CanvasSyncManager()
async def get_canvas_sync_manager() -> CanvasSyncManager:
    """Menyediakan instance singleton dari CanvasSyncManager."""
    return canvas_sync_manager_instance


AuthInfoDep = Annotated[Dict[str, Any], Depends(get_current_user_and_client)]
EmbeddingServiceDep = Annotated[IEmbeddingService, Depends(get_embedding_service)]
JudgeChainDep = Annotated[Runnable, Depends(get_judge_chain_singleton)]

# --- Layanan ---
ConversationListServiceDep = Annotated[ConversationListService, Depends(get_conversation_list_service)]
ConversationMessagesServiceDep = Annotated[ConversationMessagesService, Depends(get_conversation_messages_service)]
StreamingTitleServiceDep = Annotated[TitleStreamService, Depends(get_streaming_title_service)]
CanvasListServiceDep = Annotated[CanvasListService, Depends(get_canvas_list_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
FreeBusyServiceDep = Annotated[FreeBusyService, Depends(get_freebusy_service)]
CalendarServiceDep = Annotated[CalendarService, Depends(get_calendar_service)]
ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]
SubscriptionServiceDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
GuestServiceDep = Annotated[GuestService, Depends(get_guest_service)]
ViewServiceDep = Annotated[ViewService, Depends(get_view_service)]
CanvasSyncManagerDep = Annotated[CanvasSyncManager, Depends(get_canvas_sync_manager)]

# --- Keamanan Resource ---
CanvasAccessDep = Annotated[Dict[str, Any], Depends(get_canvas_access)] 
CanvasAdminAccessDep = Annotated[Dict[str, Any], Depends(get_canvas_admin_access)]
WorkspaceMemberDep = Annotated[Dict[str, Any], Depends(get_current_workspace_member)] 
WorkspaceAdminAccessDep = Annotated[Dict[str, Any], Depends(get_workspace_admin_access)]
ScheduleAccessDep = Annotated[Dict[str, Any], Depends(get_schedule_access)]
GuestAccessDep = Annotated[Dict[str, Any], Depends(get_guest_access)]
CalendarAccessDep = Annotated[Dict[str, Any], Depends(get_calendar_access)]
CalendarEditorAccessDep = Annotated[Dict[str, Any], Depends(get_calendar_editor_access)]
SubscriptionDeleteAccessDep = Annotated[Dict[str, Any], Depends(get_subscription_delete_access)]