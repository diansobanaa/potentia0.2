# File: backend/app/services/chat_engine/tools/registry.py
# (Diperbarui v3.2 - Menambahkan canvas_tools)

import logging
from typing import Dict
from langchain_core.tools import BaseTool, tool

logger = logging.getLogger(__name__)

# Temporary stub tools until real implementations are ready
@tool
def create_canvas_block_stub(title: str, content: str) -> str:
    """Membuat block di canvas (stub)."""
    return f"Canvas block '{title}' created (stub)"

@tool
def create_schedule_stub(title: str, start_time: str) -> str:
    """Membuat jadwal (stub)."""
    return f"Schedule '{title}' created (stub)"

def _initialize_registry() -> Dict[str, BaseTool]:
    """Inisialisasi tool registry dengan stub tools."""
    registry = {}
    
    # Use stub tools for now
    registry["create_canvas_block"] = create_canvas_block_stub
    registry["create_schedule_tool"] = create_schedule_stub
    
    logger.info(f"Tool registry dibuat. {len(registry)} tools terdaftar (stub mode).")
    return registry

# Global instance
TOOL_REGISTRY_INSTANCE = _initialize_registry()