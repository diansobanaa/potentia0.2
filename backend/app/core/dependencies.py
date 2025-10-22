from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from uuid import UUID
from typing import Union

from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.db.queries.workspace_queries import check_user_membership
from app.models.user import User, SubscriptionTier

security = HTTPBearer(auto_error=False)

class GuestUser:
    id: Union[UUID, None] = None
    is_guest: bool = True
    subscription_tier: SubscriptionTier = SubscriptionTier.user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        if user_response.user is None:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        profile_response = supabase.table("Users").select("*").eq("user_id", user_response.user.id).single().execute()
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User profile not found.")
        
        profile_data = profile_response.data
        return User(
            id=profile_data["user_id"], 
            email=profile_data["email"], 
            name=profile_data.get("name"),
            subscription_tier=profile_data.get("subscription_tier", SubscriptionTier.user)
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

async def get_current_user_or_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Union[User, GuestUser]:
    if credentials:
        try:
            return await get_current_user(credentials)
        except HTTPException:
            return GuestUser()
    else:
        return GuestUser()

async def get_user_tier(current_user: User = Depends(get_current_user)) -> SubscriptionTier:
    return current_user.subscription_tier

async def require_pro_user(tier: SubscriptionTier = Depends(get_user_tier)):
    if tier not in [SubscriptionTier.pro, SubscriptionTier.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Pro subscription."
        )
    return tier

async def require_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.subscription_tier != SubscriptionTier.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )
    return current_user

async def get_current_workspace_member(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user)
):
    from app.db.queries.workspace_queries import check_user_membership
    
    membership = check_user_membership(workspace_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace."
        )
    return {"membership": membership, "user": current_user}

async def get_canvas_access(canvas_id: UUID, current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest)):
    if isinstance(current_user, GuestUser):
        raise HTTPException(status_code=401, detail="Authentication required to access canvas.")
    
    from app.db.queries.canvas_queries import get_canvas_by_id
    from app.db.queries.workspace_queries import check_user_membership

    canvas = get_canvas_by_id(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found.")
    
    if canvas.get("user_id") and str(canvas["user_id"]) == str(current_user.id):
        return canvas
    
    if canvas.get("workspace_id"):
        membership = check_user_membership(UUID(canvas["workspace_id"]), current_user.id)
        if membership:
            return canvas
            
    raise HTTPException(status_code=403, detail="Access denied to this canvas.")