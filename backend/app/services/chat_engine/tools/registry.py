# File: backend/app/services/chat_engine/tools/registry.py
# (Diperbarui v3.2 - Menambahkan canvas_tools)

import logging
from typing import Dict, Callable, Any

# Impor fungsi tool kita
from .external_tools import search_online
from .calendar_tools import create_schedule_tool
# [BARU v3.2] Impor tool canvas
from .canvas_tools import create_canvas_block

logger = logging.getLogger(__name__)

def get_tool_registry() -> Dict[str, Callable[..., Any]]:
    """
    Membuat dan mengembalikan registry (kamus) dari semua tools
    yang tersedia untuk agen.
    """
    
    registry = {
        # Nama fungsi harus sama dengan yang dipanggil LLM
        "search_online": search_online,
        "create_schedule_tool": create_schedule_tool,
        "create_canvas_block": create_canvas_block, # [BARU v3.2]
    }
    
    logger.info(f"Tool registry dibuat. {len(registry)} tools terdaftar.")
    return registry

# --- Instance Singleton ---
TOOL_REGISTRY_INSTANCE = get_tool_registry()