# File: backend/app/core/dependencies.py

"""
Manajemen Ketergantungan (Dependency Injection) Inti Aplikasi.
"""
import logging
import asyncio
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
from typing import Union, Dict, Any, Annotated, List, Tuple, Optional
from supabase import Client
from postgrest.exceptions import APIError
import httpx
from supabase.lib.client_options import ClientOptions
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable 

# Impor dari aplikasi kita
from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.models.user import User, SubscriptionTier

# --- Impor untuk Services (Business Logic Layer) ---
from app.services.interfaces import IEmbeddingService
from app.services.embedding_service import GeminiEmbeddingService
from app.services.chat_engine.judge_chain import get_judge_chain
from app.services.conversations_list_service import ConversationListService
from app.services.conversation_messages_service import ConversationMessagesService
from app.services.title_stream_service import TitleStreamService
from app.services.canvas_list_service import CanvasListService
from app.services.user.user_service import UserService
from app.services.workspace.workspace_service import WorkspaceService
from app.services.user.user_service import UserService
from app.services.calendar.freebusy_service import FreeBusyService
from app.services.calendar.calendar_service import CalendarService
from app.services.calendar.schedule_service import ScheduleService
from app.services.calendar.subscription_service import SubscriptionService
from app.services.calendar.guest_service import GuestService
from app.services.calendar.view_service import ViewService


# --- Impor untuk MODELS ---
from app.models.workspace import MemberRole 
from app.models.canvas import CanvasRole
from app.models.schedule import CalendarVisibility, SubscriptionRole, Schedule
from app.models.schedule import RsvpStatus, GuestRole

# --- Impor untuk DATABASE ---
from app.db.queries.canvas.canvas_queries import get_canvas_by_id, check_user_canvas_access
from app.db.queries.workspace.workspace_queries import check_user_membership
from app.db.queries.calendar.calendar_queries import get_calendar_by_id, get_user_subscription
from app.db.queries.calendar.calendar_queries import (
    get_calendar_by_id, get_user_subscription, get_schedule_by_id
)


# --- Konfigurasi Awal ---
security = HTTPBearer(auto_error=False)
supabase_anon_client = get_supabase_client()
logger = logging.getLogger(__name__)

# --- Representasi Pengguna Tamu ---
class GuestUser:
    id: Union[UUID, None] = None
    is_guest: bool = True
    subscription_tier: SubscriptionTier = SubscriptionTier.user
    def __init__(self):
        self.client = supabase_anon_client

# =======================================================================
# === FUNGSI-FUNGSI DEPENDENSI  ===
# =======================================================================

async def get_current_user_and_client(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Dependable Inti: Validasi token, buat authed_client, ambil user."""
    if not credentials:
        logger.warning("Upaya akses ditolak: Tidak ada header otentikasi.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    token = credentials.credentials
    user_id: Optional[str] = None
    user_response = None 
    
    try:
        validation_client = Client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        logger.debug("Memvalidasi token dengan client.auth.get_user(token)...")
        user_response = validation_client.auth.get_user(token) 
        
        if user_response.user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user session")
        user_id = user_response.user.id
        logger.debug(f"Token valid untuk user_id: {user_id}")
        
    except APIError as e:
         logger.error(f"Supabase Auth APIError saat validasi token: {getattr(e, 'message', str(e))}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token validation failed: {getattr(e, 'message', str(e))}")
    except Exception as e:
        logger.error(f"Error tak terduga saat validasi token: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate token: {str(e)}")
        
    try:
        sync_http_client = httpx.Client(http1=True, http2=False)
        options = ClientOptions(httpx_client=sync_http_client)
        authed_client = Client(
            supabase_url=settings.SUPABASE_URL, 
            supabase_key=settings.SUPABASE_ANON_KEY,
            options=options 
        )
        
        logger.debug("Menyetel header Authorization manual untuk authed_client...")
        authed_client.options.headers["Authorization"] = f"Bearer {token}"
        
        # (Kita biarkan 'set_session' dihapus untuk menghindari error 'session'.)

        logger.debug(f"Mengambil profil internal untuk user_id: {user_id}")
        profile_response = authed_client.table("Users").select("*").eq("user_id", user_id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User profile not found in internal database.")
            
        profile_data = profile_response.data
        
        # (Perbaikan dari error 'ValidationError' sebelumnya)
        user_model = User.model_validate(profile_data)
        
        logger.debug("Otentikasi dan pengambilan profil berhasil.")
        return {"user": user_model, "client": authed_client}
        
    except Exception as e:
        logger.error(f"Error setelah validasi token (saat ambil profil/buat klien): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error after auth: {str(e)}")

async def get_current_user(auth_info: dict = Depends(get_current_user_and_client)) -> User:
    return auth_info["user"]

async def get_current_user_or_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    if credentials:
        try:
            return await get_current_user_and_client(credentials)
        except HTTPException:
            return {"user": GuestUser(), "client": supabase_anon_client}
    else:
        return {"user": GuestUser(), "client": supabase_anon_client}

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

async def get_current_workspace_member( 
    workspace_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client)
):
    """
    Dependency Keamanan (Sudah Ada):
    Memeriksa apakah pengguna yang login adalah anggota dari workspace_id.
    Melempar 403 Forbidden jika bukan anggota.
    Ini adalah gerbang dasar untuk 'melihat' (GET).
    """
    current_user: User = auth_info["user"]
    authed_client: Client = auth_info["client"]
    membership = await check_user_membership(authed_client, workspace_id, current_user.id)
    
    if not membership:
        logger.warning(f"Akses DITOLAK (Bukan Anggota) untuk user {current_user.id} ke workspace {workspace_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace.")
        
    logger.debug(f"Akses DITERIMA (Anggota) untuk user {current_user.id} ke workspace {workspace_id}.")
    # Kembalikan semua info yang relevan untuk digunakan oleh endpoint
    return {
        "membership": membership, 
        "user": current_user, 
        "client": authed_client,
        "role": membership.get("role", MemberRole.guest.value) # Ekstrak role
    }


async def get_workspace_admin_access(
    access_info: Dict[str, Any] = Depends(get_current_workspace_member)
) -> Dict[str, Any]:
    """
    Dependency Keamanan (Baru):
    Gerbang yang lebih ketat untuk aksi administratif (Invite, Patch, Delete).
    
    Fitur:
    Dependency ini bergantung pada 'get_current_workspace_member', 
    memastikan pengguna adalah anggota, LALU memeriksa apakah
    role anggota tersebut adalah 'admin'.
    """
    user_role = access_info.get("role")
    
    # Hanya 'admin' yang boleh melanjutkan
    if user_role != MemberRole.admin.value:
        user_id = access_info["user"].id
        workspace_id = access_info["membership"]["workspace_id"]
        logger.warning(f"Akses DITOLAK (Bukan Admin) untuk user {user_id} ke workspace {workspace_id}. Role: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an admin of this workspace to perform this action."
        )
        
    logger.debug(f"Akses Admin DITERIMA untuk workspace {access_info['membership']['workspace_id']}.")
    return access_info # Kembalikan info yang samaurn {"membership": membership, "user": current_user, "client": authed_client}

async def get_canvas_access( 
    canvas_id: UUID,
    auth_info: dict = Depends(get_current_user_or_guest)
) -> Dict[str, Any]:
    """
    Dependency Keamanan:
    Memeriksa otentikasi DAN otorisasi untuk satu canvas.
    
    Mengembalikan dict access_info yang berisi:
    { "canvas": ..., "user": ..., "client": ..., "role": <CanvasRole> }
    
    Role yang mungkin: 'owner', 'admin' (dari workspace), 'editor', 'viewer', 'member' (dari workspace).
    """
    current_user = auth_info["user"]
    authed_client: Client = auth_info["client"]
    
    if isinstance(current_user, GuestUser):
        raise HTTPException(status_code=401, detail="Authentication required.")

    # 1. Ambil data canvas (Sudah diperbaiki dengan maybe_single())
    canvas = await asyncio.to_thread(get_canvas_by_id, authed_client, canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found.")

    access_info = {"canvas": canvas, "user": current_user, "client": authed_client}
    
    # 2. Cek Jalur Personal (Prioritas 1: Pemilik)
    if canvas.get("user_id") and str(canvas["user_id"]) == str(current_user.id):
        logger.debug(f"Akses canvas {canvas_id} diberikan (Jalur: Personal Owner).")
        access_info["role"] = "owner" # 'owner' adalah role tertinggi
        return access_info

    # 3. Cek Jalur Workspace (Prioritas 2)
    if canvas.get("workspace_id"):
        membership = await check_user_membership(authed_client, UUID(canvas["workspace_id"]), current_user.id)
        if membership:
            workspace_role = membership.get("role", MemberRole.guest.value)
            logger.debug(f"Akses canvas {canvas_id} diberikan (Jalur: Workspace, Role: {workspace_role}).")
            # Terjemahkan role workspace ke role canvas
            # (Asumsi 'admin' workspace = 'admin' di canvas)
            access_info["role"] = workspace_role 
            return access_info

    # 4. Cek Jalur Invite / CanvasAccess (Prioritas 3)
    direct_access = await check_user_canvas_access(authed_client, canvas_id, current_user.id)
    if direct_access:
        canvas_role = direct_access.get("role", CanvasRole.viewer.value)
        logger.debug(f"Akses canvas {canvas_id} diberikan (Jalur: Invite, Role: {canvas_role}).")
        access_info["role"] = canvas_role
        return access_info

    logger.warning(f"Akses DITOLAK untuk user {current_user.id} ke canvas {canvas_id}.")
    raise HTTPException(status_code=403, detail="Access denied to this canvas.")

# --- [GERBANG KHUSUS ADMIN/EDITOR] ---
async def get_canvas_admin_access(
    access_info: Dict[str, Any] = Depends(get_canvas_access)
) -> Dict[str, Any]:
    """
    Dependency Keamanan yang Lebih Ketat.
    
    Memastikan pengguna tidak hanya memiliki akses, tetapi memiliki
    akses level TERTINGGI ('owner' atau 'admin' workspace).
    
    Komentar untuk Selanjutnya: Kita bisa perluas ini untuk 'editor' 
    dari CanvasAccess jika diperlukan.
    """
    user_role = access_info.get("role")
    
    # Tentukan role apa yang boleh mengundang/menghapus
    # (Saat ini: Pemilik canvas ATAU Admin workspace)
    admin_roles = ["owner", MemberRole.admin.value] 
    
    if user_role not in admin_roles:
        logger.warning(f"Akses admin DITOLAK ke canvas {access_info['canvas']['canvas_id']}. Role pengguna: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an owner or admin to perform this action."
        )
        
    logger.debug(f"Akses admin DITERIMA untuk canvas {access_info['canvas']['canvas_id']} (Role: {user_role}).")
    return access_info

async def get_guest_access(
    schedule_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client) 
) -> Dict[str, Any]:
    """
    Dependency Keamanan (Baru - TODO-API-5):
    Memeriksa apakah pengguna yang login adalah TAMU (GUEST)
    yang diundang ke 'schedule_id' ini.
    
    Digunakan untuk endpoint 'PATCH .../respond' (RSVP).
    """
    current_user: User = auth_info["user"]
    authed_client: Client = auth_info["client"]

    def sync_db_call() -> Optional[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedule_guests") \
                .select("*") \
                .eq("schedule_id", str(schedule_id)) \
                .eq("user_id", str(current_user.id)) \
                .eq("response_status", RsvpStatus.pending.value)\
                .maybe_single() \
                .execute()
            
            return response.data if response.data else None
            
        except APIError as e:
            logger.error(f"APIError get_guest_access: {e.message}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error get_guest_access (sync): {e}", exc_info=True)
            return None

    try:
        guest_data = await asyncio.to_thread(sync_db_call)
        
        if not guest_data:
            logger.warning(f"Gagal get_guest_access: User {current_user.id} bukan tamu 'pending' di schedule {schedule_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Anda tidak diundang ke acara ini atau sudah merespons."
            )
        
        # Kembalikan info tamu dan info auth
        return {"guest": guest_data, "user": current_user, "client": authed_client}

    except Exception as e:
        logger.error(f"Error di get_guest_access (async): {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Gagal memvalidasi akses tamu.")
    

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

async def get_user_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> UserService:
    user = auth_info["user"]
    client = auth_info["client"]
    return UserService(authed_client=client, user=user)

async def get_workspace_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> WorkspaceService:
    """Dependency injector untuk WorkspaceService."""
    user = auth_info["user"]
    client = auth_info["client"]
    return WorkspaceService(authed_client=client, user=user)


## calendar dependencies
async def get_calendar_access(
    calendar_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client)
) -> Dict[str, Any]:
    """
    Dependency Keamanan (Baru):
    Memeriksa otentikasi DAN otorisasi untuk satu 'calendar_id'.
    
    Fitur (Sesuai Rencana v1.2):
    1. Mengambil kalender.
    2. Memeriksa visibilitas (public, workspace).
    3. Memeriksa langganan (subscription) pribadi.
    
    Mengembalikan dict access_info:
    { "calendar": ..., "user": ..., "client": ..., "role": <SubscriptionRole> }
    """
    current_user: User = auth_info["user"]
    authed_client: Client = auth_info["client"]

    # --- 1. Ambil Data Kalender ---
    calendar = await get_calendar_by_id(authed_client, calendar_id)
    if not calendar:
        logger.warning(f"Gagal get_calendar_access: Calendar {calendar_id} tidak ditemukan.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found.")

    access_info = {"calendar": calendar, "user": current_user, "client": authed_client}
    
    # --- 2. Periksa Jalur Akses (Sesuai Prioritas) ---

    # Jalur 1: Apakah pengguna adalah Pemilik (Owner) kalender pribadi?
    if calendar.get("owner_user_id") and str(calendar["owner_user_id"]) == str(current_user.id):
        logger.debug(f"Akses Kalender {calendar_id} diberikan (Jalur: Personal Owner).")
        access_info["role"] = SubscriptionRole.owner
        return access_info

    # Jalur 2: Apakah ini Kalender Publik?
    if calendar.get("visibility") == CalendarVisibility.public.value:
        logger.debug(f"Akses Kalender {calendar_id} diberikan (Jalur: Public).")
        access_info["role"] = SubscriptionRole.viewer # Akses publik selalu read-only
        return access_info

    # Jalur 3: Apakah ini Kalender Workspace?
    workspace_id_str = calendar.get("workspace_id")
    if workspace_id_str:
        membership = await check_user_membership(authed_client, UUID(workspace_id_str), current_user.id)
        if membership:
            # Pengguna adalah anggota workspace
            if calendar.get("visibility") == CalendarVisibility.workspace.value:
                logger.debug(f"Akses Kalender {calendar_id} diberikan (Jalur: Workspace Member + Visibility).")
                # Terjemahkan role workspace ke role kalender
                ws_role = membership.get("role", MemberRole.guest.value)
                access_info["role"] = SubscriptionRole.editor if ws_role == MemberRole.admin.value else SubscriptionRole.viewer
                return access_info
            
            # Fallback: Jika visibility 'private' tapi di dalam workspace,
            # kita harus cek 'CalendarSubscriptions' (Jalur 4)
            pass 

    # Jalur 4: Apakah pengguna diundang secara spesifik? (Invite Pribadi)
    subscription = await get_user_subscription(authed_client, current_user.id, calendar_id)
    if subscription:
        sub_role = subscription.get("role", SubscriptionRole.viewer.value)
        logger.debug(f"Akses Kalender {calendar_id} diberikan (Jalur: Invite/Subscription). Role: {sub_role}")
        access_info["role"] = sub_role
        return access_info

    # Fallback: Jika semua gagal
    logger.warning(f"Akses DITOLAK untuk user {current_user.id} ke kalender {calendar_id}.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this calendar.")


async def get_calendar_editor_access(
    access_info: Dict[str, Any] = Depends(get_calendar_access)
) -> Dict[str, Any]:
    """
    Dependency Keamanan (Baru - Lebih Ketat):
    Memastikan pengguna memiliki hak 'owner' atau 'editor' di kalender.
    Ini akan melindungi endpoint POST, PATCH, dan DELETE.
    """
    user_role = access_info.get("role")
    
    # Tentukan role apa yang boleh mengedit
    admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value] 
    
    if user_role not in admin_roles:
        calendar_id = access_info['calendar']['calendar_id']
        logger.warning(f"Akses Editor DITOLAK ke kalender {calendar_id}. Role pengguna: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an owner or editor of this calendar to perform this action."
        )
        
    logger.debug(f"Akses Editor DITERIMA untuk kalender {access_info['calendar']['calendar_id']} (Role: {user_role}).")
    return access_info

async def get_schedule_access(
    schedule_id: UUID,
    # Panggil dependency 'get_current_user' untuk auth
    auth_info: dict = Depends(get_current_user_and_client) 
) -> Dict[str, Any]:
    """
    Dependency Keamanan (Baru - TODO-DEP-3):
    Memeriksa apakah pengguna memiliki akses ke 'schedule_id'
    dengan cara memeriksa izin mereka di 'calendar_id' induk.
    
    Mengembalikan dict access_info:
    { "schedule": ..., "calendar": ..., "user": ..., "client": ..., "role": ... }
    """
    current_user: User = auth_info["user"]
    authed_client: Client = auth_info["client"]

    # 1. Ambil data Acara (Schedule)
    schedule = await get_schedule_by_id(authed_client, schedule_id)
    if not schedule:
        logger.warning(f"Gagal get_schedule_access: Schedule {schedule_id} tidak ditemukan.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
        
    calendar_id = schedule.get("calendar_id")
    if not calendar_id:
         raise HTTPException(status_code=500, detail="Integritas data error: Acara tidak memiliki kalender.")

    try:
        # 2. Panggil dependency 'get_calendar_access'
        # Ini akan menjalankan semua 4 jalur keamanan (Owner, Public, Workspace, Invite)
        # dan melempar 403/404 jika pengguna tidak punya akses ke kalender induk.
        calendar_access_info = await get_calendar_access(
            calendar_id, auth_info
        )
        
        # 3. Gabungkan info dan kembalikan
        logger.debug(f"Akses Schedule {schedule_id} diberikan (via Calendar {calendar_id}).")
        
        # Gabungkan dict
        access_info = {
            "schedule": schedule,
            **calendar_access_info 
        }
        return access_info

    except HTTPException as e:
        # Jika 'get_calendar_access' gagal (403/404), teruskan error-nya
        logger.warning(f"Gagal get_schedule_access: Akses ditolak ke kalender induk {calendar_id}.")
        raise e
    

async def get_freebusy_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> FreeBusyService:
    """Dependency injector untuk FreeBusyService."""
    return FreeBusyService(auth_info=auth_info)

async def get_calendar_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> CalendarService:
    """Dependency injector untuk CalendarService."""
    return CalendarService(auth_info=auth_info)

async def get_schedule_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> ScheduleService:
    """Dependency injector untuk ScheduleService."""
    return ScheduleService(auth_info=auth_info)

async def get_subscription_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> SubscriptionService:
    """Dependency injector untuk SubscriptionService."""
    return SubscriptionService(auth_info=auth_info)

async def get_guest_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> GuestService:
    """Dependency injector untuk GuestService."""
    return GuestService(auth_info=auth_info)

async def get_view_service(
    auth_info: Dict[str, Any] = Depends(get_current_user_and_client),
) -> ViewService:
    """Dependency injector untuk ViewService."""
    return ViewService(auth_info=auth_info)


AuthInfoDep = Annotated[Dict[str, Any], Depends(get_current_user_and_client)]
EmbeddingServiceDep = Annotated[IEmbeddingService, Depends(get_embedding_service)]
JudgeChainDep = Annotated[Runnable, Depends(get_judge_chain_singleton)]
JudgeLLMDep = Annotated[ChatGoogleGenerativeAI, Depends(get_judge_chain_singleton)]

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

# --- Keamanan Resource (Lama) ---
CanvasAccessDep = Annotated[Dict[str, Any], Depends(get_canvas_access)] 
CanvasAdminAccessDep = Annotated[Dict[str, Any], Depends(get_canvas_admin_access)]
WorkspaceMemberDep = Annotated[Dict[str, Any], Depends(get_current_workspace_member)] 
WorkspaceAdminAccessDep = Annotated[Dict[str, Any], Depends(get_workspace_admin_access)]
ScheduleAccessDep = Annotated[Dict[str, Any], Depends(get_schedule_access)]
GuestAccessDep = Annotated[Dict[str, Any], Depends(get_guest_access)]
CalendarAccessDep = Annotated[Dict[str, Any], Depends(get_calendar_access)]
CalendarEditorAccessDep = Annotated[Dict[str, Any], Depends(get_calendar_editor_access)]