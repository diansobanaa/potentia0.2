"""
Main chat orchestration service.
"""
import logging
import uuid
from typing import AsyncGenerator, Optional
from uuid import UUID
from fastapi import BackgroundTasks
from langchain_core.messages import HumanMessage
from datetime import datetime, timezone  # <-- add import

from app.models.user import User
from app.services.chat_engine.helpers import MessageLoader, PermissionHelper, TokenCounter
from app.services.chat_engine.streaming_service import StreamingService
from app.db.queries.conversation import conversation_queries
from app.core.config import settings
from app.services.chat_engine.agent_prompts import AGENT_SYSTEM_PROMPT  # ensure imported

logger = logging.getLogger(__name__)


class ChatService:
    """Main service for chat orchestration."""
    
    @staticmethod
    async def ensure_conversation(client, user_id: UUID, conversation_id: Optional[UUID]) -> UUID:
        """
        Centralized guard:
        - If conversation_id is None: create new conversation and return its ID.
        - If provided: try fetch; if not found → create new and return the new ID.
        """
        if conversation_id is None:
            # Create new conversation
            new_conversation_id = uuid.uuid4()
            await conversation_queries.get_or_create_conversation(
                client,
                user_id,
                new_conversation_id
            )
            logger.info(f"Created new conversation {new_conversation_id} for user {user_id}")
            return new_conversation_id
        else:
            # Check if conversation exists
            conversation = await conversation_queries.get_conversation_by_id(
                client,
                conversation_id
            )
            if conversation is None:
                # If not found, create new conversation
                await conversation_queries.get_or_create_conversation(
                    client,
                    user_id,
                    conversation_id
                )
                logger.info(f"Conversation {conversation_id} not found. Created new conversation with the same ID for user {user_id}")
            return conversation_id

    @staticmethod
    async def create_chat_stream(
        user: User,
        client,
        message: str,
        conversation_id: Optional[UUID],
        background_tasks: BackgroundTasks,
        embedding_service,
        langgraph_agent,
        llm_config: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """Main entry point for creating a chat stream."""
        # Generate IDs
        request_id = str(uuid.uuid4())
        conversation_id = conversation_id or uuid.uuid4()
        
        logger.info(f"Starting chat stream for user {user.id}, conversation {conversation_id}")
        
        # 1. Ensure conversation exists
        await conversation_queries.get_or_create_conversation(
            client,
            user.id,
            conversation_id
        )
        
        # 2. Load chat history
        chat_history = await MessageLoader.load_history(
            client=client,
            user_id=user.id,
            conversation_id=conversation_id,
            limit=40
        )
        
        # 3. Get user permissions
        permissions = PermissionHelper.get_user_permissions(user)
        
        # 4. Append current message to history
        full_history = chat_history + [HumanMessage(content=message)]
        
        # 5. Prepare auth_info for dependency injection
        auth_info = {"user": user, "client": client}
        
        # 6. Stream agent response & capture final state
        response_chunks = []
        final_state = None
        
        # --- FIX: provide current_time when formatting AGENT_SYSTEM_PROMPT for token estimation ---
        try:
            current_time_str = f"Informasi Waktu: Waktu saat ini adalah {datetime.now(timezone.utc).strftime('%A, %Y-%m-%d %H:%M %Z')}."
        except Exception:
            current_time_str = "Informasi Waktu: Waktu saat ini tidak dapat ditentukan."

        # Estimate classify and agent prompt tokens safely
        try:
            classify_prompt_tokens = TokenCounter.count_tokens(
                # If you have CLASSIFY_INTENT_PROMPT, keep as-is. Otherwise leave estimation minimal.
                # ...existing code or computed classify prompt...
                ""
            )
        except Exception:
            classify_prompt_tokens = 0

        try:
            agent_prompt_tokens = TokenCounter.count_tokens(
                AGENT_SYSTEM_PROMPT.format(
                    current_time=current_time_str,
                    compressed_context="(Tidak ada konteks RAG)",
                    chat_history=await MessageLoader.load_history(client, user.id, conversation_id, limit=40),  # minimal safe value
                    user_message=message
                )
            )
        except Exception:
            # Fallback: count only user_message to avoid KeyError
            agent_prompt_tokens = TokenCounter.count_tokens(message)

        logger.info(f"📊 ESTIMATED input tokens: classify={classify_prompt_tokens}, agent={agent_prompt_tokens}, total={classify_prompt_tokens + agent_prompt_tokens}")
        # --- end FIX ---

        # Log llm_config before passing to streaming service
        if llm_config:
            logger.info(
                f"📤 ChatService passing llm_config to StreamingService: "
                f"{llm_config}"
            )
        else:
            logger.warning(
                "⚠️  ChatService: llm_config is None, "
                "will use DEFAULT_MODEL"
            )

        async for sse_event in StreamingService.stream_agent_response(
            langgraph_agent=langgraph_agent,
            request_id=request_id,
            user_id=str(user.id),
            conversation_id=str(conversation_id),
            user_message=message,
            chat_history=full_history,
            permissions=permissions,
            auth_info=auth_info,
            embedding_service=embedding_service,
            background_tasks=background_tasks,
            llm_config=llm_config  # pass-through
        ):
            # Capture token chunks
            if '"type": "token_chunk"' in sse_event:
                try:
                    import json
                    event_data = json.loads(sse_event.strip())
                    if event_data.get("type") == "token_chunk":
                        response_chunks.append(event_data.get("payload", "") or "")
                except Exception:
                    pass

            # Capture final_state
            if '"type": "final_state"' in sse_event:
                try:
                    import json
                    event_data = json.loads(sse_event.strip())
                    final_state = event_data.get("payload", {}) or {}
                    logger.debug(f"Captured final_state: {final_state}")
                except Exception as e:
                    logger.error(f"Failed to parse final_state: {e}")

            yield sse_event

        # Persist messages with accurate token usage
        final_response = "".join(response_chunks)

        # Parse final_state
        if final_state:
            total_input_tokens = final_state.get("input_token_count") or 0
            total_output_tokens = final_state.get("output_token_count") or 0
            api_call_count = final_state.get("api_call_count", 0)
            model_used = final_state.get("model_used") or \
                settings.DEFAULT_MODEL
        else:
            # Fallback: estimate input tokens from message
            total_input_tokens = TokenCounter.count_tokens(message)
            total_output_tokens = 0
            api_call_count = 0
            model_used = settings.DEFAULT_MODEL
        
        # User-only tokens
        user_input_tokens = TokenCounter.count_tokens(message)

        logger.info(
            f"Token summary (conv={conversation_id}) - total_input={total_input_tokens}, "
            f"total_output={total_output_tokens}, api_calls={api_call_count}, model={model_used}"
        )
        
        background_tasks.add_task(
            ChatService._save_messages_after_stream,
            client=client,
            user_id=user.id,
            conversation_id=conversation_id,
            user_message=message,
            ai_response=final_response,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            user_input_tokens=user_input_tokens,
            api_call_count=api_call_count,  # NEW parameter
            model_used=model_used,
        )

        logger.info(f"Chat stream completed for request {request_id}")
    
    @staticmethod
    async def _save_messages_after_stream(
        client,
        user_id: UUID,
        conversation_id: UUID,
        user_message: str,
        ai_response: str,
        total_input_tokens: int,
        total_output_tokens: int,
        user_input_tokens: int,
        api_call_count: int,  # NEW parameter
        model_used: str,
    ):
        """Save messages with accurate token counts and API call count."""
        try:
            # User message (no API calls for user input)
            user_message_data = {
                "user_id": str(user_id),
                "conversation_id": str(conversation_id),
                "role": "user",
                "content": user_message,
                "model_used": None,
                "token_count": int(total_input_tokens),
                "input_tokens": int(user_input_tokens),
                "output_tokens": 0,
                "api_call_count": 0  # NEW: User messages don't make API calls
            }
            
            await client.table("messages").insert(user_message_data).execute()
            logger.debug(f"Saved user message for conversation {conversation_id}")
            
            # AI message (with API call count)
            if ai_response:
                ai_message_data = {
                    "user_id": str(user_id),
                    "conversation_id": str(conversation_id),
                    "role": "ai",
                    "content": ai_response,
                    "model_used": model_used,
                    "token_count": int(total_output_tokens),
                    "input_tokens": 0,
                    "output_tokens": int(total_output_tokens),
                    "api_call_count": int(api_call_count)  # NEW: Exact count of API calls
                }
                
                await client.table("messages").insert(ai_message_data).execute()
                logger.debug(f"Saved AI response for conversation {conversation_id} ({api_call_count} API calls)")
            
            logger.info(f"Messages saved successfully for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save messages for conversation {conversation_id}: {e}", exc_info=True)
