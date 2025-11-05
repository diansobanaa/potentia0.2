"""Tool executors dengan proper dependency injection."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from supabase import Client as SupabaseClient
import logging

logger = logging.getLogger(__name__)


class ToolExecutor(ABC):
    """Base class untuk semua tool executors."""
    
    @abstractmethod
    async def execute(
        self, 
        authed_client: SupabaseClient,
        **kwargs
    ) -> Any:
        """Execute tool dengan parameters."""
        pass


class FindHistoryExecutor(ToolExecutor):
    """Executor untuk find_relevant_conversation_history tool."""
    
    def __init__(self, query_service=None):
        # Dependency injection untuk testing
        from app.db.queries.conversation_queries import find_relevant_history
        self.query_service = query_service or find_relevant_history
    
    async def execute(
        self,
        authed_client: SupabaseClient,
        query_embedding: List[float],
        **kwargs
    ) -> List[Dict]:
        """Execute history search."""
        logger.info("Executing find_relevant_conversation_history")
        
        try:
            result = self.query_service(authed_client, query_embedding)
            logger.info(f"Found {len(result)} history items")
            return result
            
        except Exception as e:
            logger.error(f"Failed to find history: {e}", exc_info=True)
            raise ToolExecutionError(
                tool_name="find_relevant_conversation_history",
                reason=str(e)
            ) from e


class FindRoleExecutor(ToolExecutor):
    """Executor untuk find_most_relevant_role tool."""
    
    def __init__(self, query_service=None):
        from app.db.queries.role_queries import find_relevant_role
        self.query_service = query_service or find_relevant_role
    
    async def execute(
        self,
        authed_client: SupabaseClient,
        query_embedding: List[float],
        **kwargs
    ) -> Dict:
        """Execute role search."""
        logger.info("Executing find_most_relevant_role")
        try:
            result = self.query_service(authed_client, query_embedding)
            logger.info(f"Found role: {result}")
            return result   
        except Exception as e:
            logger.error(f"Failed to find role: {e}", exc_info=True)
            raise ToolExecutionError(
                tool_name="find_most_relevant_role",
                reason=str(e)
            ) from e


# Custom exception
class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Tool '{tool_name}' failed: {reason}")