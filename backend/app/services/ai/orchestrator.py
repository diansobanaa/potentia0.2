"""Orchestrator untuk Gemini tool calling workflow."""
from typing import Dict, Any, List
from supabase import Client as SupabaseClient
import google.generativeai as genai
import logging

from app.services.ai.gemini_client import GeminiClient
from app.services.ai.tool_registry import tool_registry
from app.services.ai.tool_executors import ToolExecutionError
from app.services.embedding_service import generate_embedding
from app.models.user import SubscriptionTier

logger = logging.getLogger(__name__)


class GeminiOrchestrator:
    """Orchestrates Gemini interactions dengan tool calling."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        embedding_service=None
    ):
        self.client = gemini_client
        self.embedding_service = embedding_service or generate_embedding
    
    async def get_response(
        self,
        authed_client: SupabaseClient,
        user_message: str,
        user_tier: SubscriptionTier
    ) -> Dict[str, Any]:
        """
        Main workflow untuk mendapatkan respons dengan tool calling.
        
        Returns:
            Dict dengan keys: status, response, metadata, debug_info
        """
        try:
            # 1. Generate embedding
            query_embedding = await self._generate_embedding(user_message)
            
            # 2. Create model dengan tools
            model = self.client.create_model(tools=tool_registry.tools)
            chat = self.client.start_chat(model)
            
            # 3. Send initial message
            response = await self._send_message(chat, user_message)
            
            # 4. Handle tool calls
            response = await self._handle_tool_calls(
                chat=chat,
                response=response,
                authed_client=authed_client,
                query_embedding=query_embedding
            )
            
            # 5. Extract final answer
            final_answer = response.text
            
            return {
                "status": "success",
                "response": final_answer,
                "metadata": {
                    "role_used": "Tool-based workflow",
                    "user_tier": user_tier.value
                },
                "debug_info": "Response generated using Tool Use workflow"
            }
            
        except ToolExecutionError as e:
            logger.error(f"Tool execution failed: {e}")
            return self._error_response(f"Tool error: {e.reason}")
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            return self._error_response("Internal AI error")
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding dengan error handling."""
        embedding = await self.embedding_service(text)
        if not embedding:
            raise ValueError("Failed to generate embedding")
        return embedding
    
    async def _send_message(self, chat, message: str):
        """Send message ke Gemini."""
        logger.debug(f"Sending message: {message[:100]}...")
        return await chat.send_message_async(message)
    
    async def _handle_tool_calls(
        self,
        chat,
        response,
        authed_client: SupabaseClient,
        query_embedding: List[float]
    ):
        """Handle semua tool calls dalam loop."""
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while self._has_function_call(response) and iteration < max_iterations:
            iteration += 1
            
            part = response.candidates[0].content.parts[0]
            function_call = part.function_call
            function_name = function_call.name
            
            logger.info(f"Tool call requested: {function_name}")
            
            # Execute tool
            try:
                result = await self._execute_tool(
                    function_name=function_name,
                    authed_client=authed_client,
                    query_embedding=query_embedding,
                    args=function_call.args
                )
                
                # Send result back
                response = await self._send_function_response(
                    chat=chat,
                    function_name=function_name,
                    result=result
                )
                
            except ToolExecutionError as e:
                # Send error response to Gemini
                response = await self._send_function_response(
                    chat=chat,
                    function_name=function_name,
                    result={"error": e.reason}
                )
        
        if iteration >= max_iterations:
            logger.warning("Max tool call iterations reached")
        
        return response
    
    async def _execute_tool(
        self,
        function_name: str,
        authed_client: SupabaseClient,
        query_embedding: List[float],
        args: Dict
    ) -> Any:
        """Execute single tool."""
        executor = tool_registry.get_executor(function_name)
        
        if not executor:
            raise ToolExecutionError(
                tool_name=function_name,
                reason="Tool not found in registry"
            )
        
        return await executor.execute(
            authed_client=authed_client,
            query_embedding=query_embedding,
            **args
        )
    
    async def _send_function_response(
        self,
        chat,
        function_name: str,
        result: Any
    ):
        """Send function result back to Gemini."""
        logger.debug(f"Sending tool response for: {function_name}")
        
        return await chat.send_message_async(
            genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=function_name,
                    response={'result': result}
                )
            )
        )
    
    def _has_function_call(self, response) -> bool:
        """Check if response contains function call."""
        try:
            return bool(response.candidates[0].content.parts[0].function_call.name)
        except (AttributeError, IndexError):
            return False
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "status": "error",
            "message": message
        }


# Factory function untuk ease of use
def create_orchestrator() -> GeminiOrchestrator:
    """Create configured orchestrator instance."""
    client = GeminiClient()
    return GeminiOrchestrator(client)