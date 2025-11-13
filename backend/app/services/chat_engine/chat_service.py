"""
Main chat orchestration service.
"""
import logging
import uuid
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import BackgroundTasks
from langchain_core.messages import HumanMessage

from app.models.user import User
from app.services.chat_engine.helpers import MessageLoader, PermissionHelper, TokenCounter
from app.services.chat_engine.streaming_service import StreamingService
from app.db.queries.conversation import conversation_queries
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatService:
    """Main service for chat orchestration."""
    
    @staticmethod
    async def create_chat_stream(
        user: User,
        client,
        message: str,
        conversation_id: Optional[UUID],
        background_tasks: BackgroundTasks,
        embedding_service,
        langgraph_agent
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
        
        # NEW: Calculate BEFORE streaming (guaranteed accurate)
        # Total input = system prompt + RAG context + history + user input
        from app.services.chat_engine.agent_prompts import AGENT_SYSTEM_PROMPT, CLASSIFY_INTENT_PROMPT
        
        # Estimate system prompts (classify + agent)
        classify_prompt_tokens = TokenCounter.count_tokens(CLASSIFY_INTENT_PROMPT.format(
            chat_history=chat_history,
            user_message=message
        ))
        
        agent_prompt_tokens = TokenCounter.count_tokens(AGENT_SYSTEM_PROMPT.format(
            compressed_context="",  # Will be filled by RAG
            chat_history=chat_history,
            user_message=message
        ))
        
        # Total estimate
        estimated_total_input = classify_prompt_tokens + agent_prompt_tokens
        
        logger.info(f"📊 ESTIMATED input tokens: classify={classify_prompt_tokens}, agent={agent_prompt_tokens}, total={estimated_total_input}")
        
        async for sse_event in StreamingService.stream_agent_response(
            langgraph_agent=langgraph_agent,
            request_id=request_id,
            user_id=str(user.id),
            conversation_id=str(conversation_id),
            user_message=message,
            chat_history=full_history,
            permissions=permissions,
            auth_info={"user": user, "client": client},
            embedding_service=embedding_service,
            background_tasks=background_tasks
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
            api_call_count = final_state.get("api_call_count", 0)  # NEW
            model_used = final_state.get("model_used") or settings.GEMINI_GENERATIVE_MODEL
        else:
            total_input_tokens = estimated_total_input
            total_output_tokens = 0
            api_call_count = 0
            model_used = settings.GEMINI_GENERATIVE_MODEL  # Fallback to default model
        
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
