"""Registry untuk semua tool definitions."""
import google.generativeai as genai
from typing import Dict, Callable, List

class ToolRegistry:
    """Centralized registry untuk tool definitions dan executors."""
    
    def __init__(self):
        self._tools: List[genai.protos.Tool] = []
        self._executors: Dict[str, Callable] = {}
    
    def register(
        self, 
        name: str, 
        description: str, 
        parameters: dict,
        executor: Callable
    ):
        """Register tool dengan executor-nya."""
        # Create tool definition
        tool = genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name=name,
                    description=description,
                    parameters=self._create_schema(parameters)
                )
            ]
        )
        
        self._tools.append(tool)
        self._executors[name] = executor
    
    def _create_schema(self, parameters: dict):
        """Helper untuk membuat parameter schema."""
        # Implementation detail...
        pass
    
    @property
    def tools(self) -> List[genai.protos.Tool]:
        """Get all registered tools."""
        return self._tools
    
    def get_executor(self, name: str) -> Callable:
        """Get executor untuk tool name."""
        return self._executors.get(name)


# Global registry instance
tool_registry = ToolRegistry()

# Register tools (bisa di file terpisah juga)
def register_default_tools():
    """Register semua default tools."""
    from app.services.ai.tool_executors import (
        FindHistoryExecutor,
        FindRoleExecutor
    )
    
    tool_registry.register(
        name="find_relevant_conversation_history",
        description="Mencari riwayat percakapan yang relevan berdasarkan vektor embedding kueri untuk mendukung respons AI yang lebih kontekstual.",
        parameters={
            'query_embedding': {
                'type': 'array',
                'items': {'type': 'number'},
                'description': 'Vector embedding...'
            }
        },
        executor=FindHistoryExecutor()
    )
    
    tool_registry.register(
        name="find_most_relevant_role",
        description="Mencari peran AI yang paling sesuai dengan kueri pengguna berdasarkan vektor embedding untuk mengoptimalkan respons AI.",
        parameters={
            'query_embedding': {
                'type': 'array',
                'items': {'type': 'number'},
                'description': 'Vector embedding...'
            }
        },
        executor=FindRoleExecutor()
    )