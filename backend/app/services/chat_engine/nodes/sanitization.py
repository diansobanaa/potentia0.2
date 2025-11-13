import re
import logging
from typing import Dict, Any

from app.services.chat_engine.agent_state import AgentState

logger = logging.getLogger(__name__)

async def sanitize_input(state: AgentState) -> Dict[str, Any]:
    """
    Node #0: Membersihkan input pengguna sebelum diproses.
    (Implementasi NFR Poin 3: Sanitasi Input PII)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: sanitize_input")
    
    user_message = state.get("user_message", "")
    
    # Regex yang kuat untuk PII
    sanitized_message = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_DIREDAKSI]", user_message, flags=re.IGNORECASE)
    sanitized_message = re.sub(r"(\+62|62|0)8[1-9][0-9]{7,10}\b", "[TELEPON_DIREDAKSI]", sanitized_message)
    sanitized_message = re.sub(r"\b\d{16}\b", "[NIK_DIREDAKSI]", sanitized_message)
    
    if sanitized_message != user_message:
        logger.warning(f"REQUEST_ID: {request_id} - Input disanitasi (PII terdeteksi).")
    
    return {
        "user_message": sanitized_message,
        "api_call_count": state.get("api_call_count", 0)  # Preserve
    }
