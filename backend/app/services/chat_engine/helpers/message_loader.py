"""
Chat history loading utilities.
"""
import logging
from typing import List, Optional
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.db.queries.conversation import message_list_queries

logger = logging.getLogger(__name__)


class MessageLoader:
    """Helper class for loading and converting chat history."""
    
    @staticmethod
    async def load_history(
        client,
        user_id: UUID,
        conversation_id: Optional[UUID],
        limit: int = 40
    ) -> List[BaseMessage]:
        """Load chat history from DB and convert to LangChain messages."""
        if not conversation_id:
            logger.debug("No conversation_id provided, returning empty history")
            return []
        
        try:
            messages_data, _ = await message_list_queries.get_conversation_messages_paginated(
                client, user_id, conversation_id, offset=0, limit=limit
            )
            
            history: List[BaseMessage] = []
            
            # Sort by created_at (ascending = oldest first)
            for msg in sorted(messages_data, key=lambda x: x['created_at']):
                content = msg.get("content", "")
                role = msg.get("role")  # Get role from DB
                
                if role == 'user':
                    history.append(HumanMessage(content=content))
                    
                elif role == 'ai':  # FIX: Changed from 'assistant' to 'ai'
                    tool_calls = msg.get("tool_calls")
                    if tool_calls:
                        history.append(AIMessage(content=content, tool_calls=tool_calls))
                    else:
                        history.append(AIMessage(content=content))
            
            logger.debug(f"Loaded {len(history)} messages for conversation {conversation_id}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to load history for conversation {conversation_id}: {e}", exc_info=True)
            return []
