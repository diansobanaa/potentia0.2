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

# Impor dari aplikasi kita
from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.models.user import User, SubscriptionTier

# --- Impor untuk Services (Business Logic Layer) ---
from app.services.interfaces import IEmbeddingService
from app.services.embedding_service import GeminiEmbeddingService
from langchain_core.runnables import Runnable 
from app.services.chat_engine.judge_chain import get_judge_chain

from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.conversations_list_service import ConversationListService
from app.services.conversation_messages_service import ConversationMessagesService
from app.services.title_stream_service import TitleStreamService
from app.services.canvas_list_service import CanvasListService
from app.services.user.user_service import UserService
from app.services.workspace.workspace_service import WorkspaceService
from app.services.user.user_service import UserService
from app.db.queries.workspace.workspace_queries import check_user_membership

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
# === FUNGSI-FUNGSI DEPENDENSI (DEFINISI DULU) ===
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
    current_user: User = auth_info["user"]
    authed_client: Client = auth_info["client"]
    membership = await check_user_membership(authed_client, workspace_id, current_user.id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace.")
    return {"membership": membership, "user": current_user, "client": authed_client}

async def get_canvas_access( 
    canvas_id: UUID,
    auth_info: dict = Depends(get_current_user_or_guest)
):
    from app.db.queries.canvas_queries import get_canvas_by_id
    current_user = auth_info["user"]
    authed_client: Client = auth_info["client"]
    if isinstance(current_user, GuestUser):
        raise HTTPException(status_code=401, detail="Authentication required.")
    canvas = await asyncio.to_thread(get_canvas_by_id, authed_client, canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found.")
    if canvas.get("user_id") and str(canvas["user_id"]) == str(current_user.id):
        return {"canvas": canvas, "user": current_user, "client": authed_client}
    if canvas.get("workspace_id"):
        membership = await check_user_membership(authed_client, UUID(canvas["workspace_id"]), current_user.id)
        if membership:
            return {"canvas": canvas, "user": current_user, "client": authed_client}
    raise HTTPException(status_code=403, detail="Access denied to this canvas.")

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


AuthInfoDep = Annotated[Dict[str, Any], Depends(get_current_user_and_client)]
EmbeddingServiceDep = Annotated[IEmbeddingService, Depends(get_embedding_service)]
CanvasAccessDep = Annotated[Dict[str, Any], Depends(get_canvas_access)] 
WorkspaceMemberDep = Annotated[Dict[str, Any], Depends(get_current_workspace_member)] 
JudgeChainDep = Annotated[Runnable, Depends(get_judge_chain_singleton)]
JudgeLLMDep = Annotated[ChatGoogleGenerativeAI, Depends(get_judge_chain_singleton)]
ConversationListServiceDep = Annotated[ConversationListService, Depends(get_conversation_list_service)]
ConversationMessagesServiceDep = Annotated[ConversationMessagesService, Depends(get_conversation_messages_service)]
StreamingTitleServiceDep = Annotated[TitleStreamService, Depends(get_streaming_title_service)]
CanvasListServiceDep = Annotated[CanvasListService, Depends(get_canvas_list_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]