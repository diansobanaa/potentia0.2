from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Union

# Model Pydantic untuk request body pesan
from app.models.conversation import MessageCreate
# Model Pydantic untuk data user
from app.models.user import User

# Dependensi untuk mendapatkan user yang sudah login
from app.core.dependencies import get_current_user, GuestUser, get_current_user_or_guest
from app.db.queries.conversation_queries import claim_guest_session, get_or_create_conversation, add_message
from app.services.ai_agent_service import run_agent_flow
from app.services.embedding_service import generate_embedding

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Mendapatkan profil pengguna yang sedang login.
    """
    return current_user

@router.post("/claim-guest-session")
async def claim_guest_session_endpoint(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Mengaitkan sesi chat guest ke akun pengguna yang baru mendaftar.
    """
    success = claim_guest_session(conversation_id, current_user.id)
    if success:
        return {"status": "success", "message": "Session claimed successfully."}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or already claimed.")

@router.post("/global-chat/send")
async def send_global_message(
    message: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Mengirim pesan ke Asisten Pribadi (konteks global).
    """
    agent_result = await run_agent_flow(
        user_id=current_user.id, 
        current_canvas_id=None, 
        user_message=message.content, 
        user_tier=current_user.subscription_tier
    )
    
    if agent_result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=agent_result.get("message", "An unknown error occurred."))

    ai_response = agent_result["response"]

    conversation = get_or_create_conversation(canvas_id=None, user_id=current_user.id)
    
    user_embedding = await generate_embedding(message.content)
    if user_embedding:
        add_message(conversation["id"], "user", message.content, user_embedding)

    ai_embedding = await generate_embedding(ai_response)
    if ai_embedding:
        add_message(conversation["id"], "ai", ai_response, ai_embedding)
    
    return {
        "type": "chat",
        "content": ai_response,
        "metadata": agent_result.get("metadata", {})
    }