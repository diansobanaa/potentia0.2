from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from typing import List

from app.models.conversation import MessageCreate, Message
from app.models.user import User
from app.core.dependencies import get_current_user_or_guest, get_canvas_access, get_current_user
from app.services.ai_agent_service import run_agent_flow
from app.services.rate_limit_service import check_guest_limit, check_user_limit
from app.services.embedding_service import generate_embedding
from app.db.queries.conversation_queries import get_or_create_conversation, add_message
from app.db.queries.canvas_queries import get_blocks_in_canvas

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"]
)

@router.post("/{canvas_id}/send")
async def send_message_in_canvas(
    canvas_id: UUID,
    message: MessageCreate,
    request: Request,
    canvas: dict = Depends(get_canvas_access),
    current_user: User = Depends(get_current_user)
):
    is_guest = current_user.is_guest
    user_id = current_user.id if not is_guest else None
    user_tier = current_user.subscription_tier

    if is_guest:
        client_ip = request.client.host
        if not check_guest_limit(client_ip):
            raise HTTPException(status_code=429, detail="You've reached the message limit for guests. Sign up for free to continue!")
    else:
        if not check_user_limit(user_id, user_tier.value):
            raise HTTPException(status_code=429, detail="You've reached your message limit for this hour. Upgrade to Pro for unlimited messages.")

    agent_result = await run_agent_flow(
        user_id=user_id, 
        current_canvas_id=canvas_id,
        user_message=message.content, 
        user_tier=user_tier
    )
    
    if agent_result["status"] == "error":
        raise HTTPException(status_code=500, detail=agent_result.get("message", "An unknown error occurred."))

    ai_response = agent_result["response"]

    conversation = get_or_create_conversation(canvas_id, user_id)
    
    user_embedding = await generate_embedding(message.content)
    if user_embedding:
        add_message(conversation["id"], "user", message.content, user_embedding)

    ai_embedding = await generate_embedding(ai_response)
    if ai_embedding:
        add_message(conversation["id"], "ai", ai_response, ai_embedding)
    
    response_data = {
        "type": "chat",
        "content": ai_response,
        "metadata": agent_result.get("metadata", {})
    }

    if is_guest:
        response_data["cta"] = {
            "message": "Enjoying the chat? Sign up to save your history and unlock more features!",
            "conversation_id": str(conversation["id"])
        }

    return response_data

@router.get("/{canvas_id}/history")
async def get_chat_history(
    canvas_id: UUID,
    canvas: dict = Depends(get_canvas_access),
    current_user: User = Depends(get_current_user)
):
    # Mengambil semua pesan dari sebuah canvas untuk ditampilkan di frontend
    # Untuk saat ini, kita kembalikan semua pesan. Di frontend nanti bisa dipaginasi.
    conversation = get_or_create_conversation(canvas_id, current_user.id)
    # Di masa depan, backend hanya mengembalikan pesan.
    # Untuk frontend, lebih baik jika backend mengembalikan metadata dan kontenks.
    # Kita akan tetapkan dengan cara sederhana dulu.
    messages = get_messages_in_conversation(conversation["id"])
    return messages