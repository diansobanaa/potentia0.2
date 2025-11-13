# File: backend/app/api/v1/endpoints/chat_actions.py
# (Diperbarui v2.9 - Perbaikan Gap #3: Injeksi Dependensi HiTL Robusta)

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from langchain_core.runnables import RunnableConfig


from app.core.dependencies import (
    AuthInfoDep, 
    LangGraphAgentDep, 
    EmbeddingServiceDep 
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat/{conversation_id}/actions",
    tags=["chat"]
)

@router.post(
    "/approve_tool",
    summary="Menyetujui eksekusi tool (Human-in-the-Loop)",
    status_code=status.HTTP_202_ACCEPTED
)
async def approve_tool_execution(
    conversation_id: UUID,
    auth_info: AuthInfoDep,
    langgraph_agent: LangGraphAgentDep,
    embedding_service: EmbeddingServiceDep,
    background_tasks: BackgroundTasks
):
    """
    Endpoint ini dipanggil oleh frontend setelah pengguna menekan
    tombol 'Setuju' pada permintaan persetujuan tool.
    (Implementasi NFR Poin 11)
    """
    user_id = str(auth_info["user"].id)
    logger.info(f"USER: {user_id} - Menyetujui tool untuk convo: {conversation_id}")

    try:
        # === [PERBAIKAN KRUSIAL v2.9 - Gap #3] ===
        # Kita harus meng-inject SEMUA dependensi yang mungkin
        # diperlukan oleh node-node berikutnya (call_tools, extract_preferences)
        # saat melanjutkan graph yang dijeda.
        config = RunnableConfig(
            configurable={
                "thread_id": str(conversation_id),
                "dependencies": {
                    "auth_info": auth_info,
                    "embedding_service": embedding_service,
                    "background_tasks": background_tasks
                }
            }
        )
        # === AKHIR PERBAIKAN ===
        
        # Panggil .ainvoke(None, ...) untuk melanjutkan graph
        # dari titik 'InterruptException'
        # Kita tidak perlu .astream_events() di sini, hanya perlu memicunya
        # Kita menggunakan 'await' untuk memastikan resume diterima
        await langgraph_agent.ainvoke(None, config=config)
        
        return {"status": "tool_approved", "message": "Eksekusi tool dilanjutkan."}
        
    except Exception as e:
        logger.error(f"Gagal melanjutkan graph (approve_tool) untuk convo {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal melanjutkan graph: {e}"
        )

# [BARU v2.9] Endpoint untuk menolak tool
@router.post(
    "/reject_tool",
    summary="Menolak eksekusi tool (Human-in-the-Loop)",
    status_code=status.HTTP_202_ACCEPTED
)
async def reject_tool_execution(
    conversation_id: UUID,
    auth_info: AuthInfoDep,
    langgraph_agent: LangGraphAgentDep,
    embedding_service: EmbeddingServiceDep,
    background_tasks: BackgroundTasks
):
    """
    Endpoint ini dipanggil oleh frontend setelah pengguna menekan
    tombol 'Tolak' pada permintaan persetujuan tool.
    """
    user_id = str(auth_info["user"].id)
    logger.info(f"USER: {user_id} - Menolak tool untuk convo: {conversation_id}")

    try:
        # Siapkan config yang sama
        config = RunnableConfig(
            configurable={
                "thread_id": str(conversation_id),
                "dependencies": {
                    "auth_info": auth_info,
                    "embedding_service": embedding_service,
                    "background_tasks": background_tasks
                }
            }
        )

        # [BARU] Panggil .ainvoke() dengan input baru
        # Ini akan "membangunkan" graph dan mengirimkan "Penolakan pengguna"
        # sebagai 'HumanMessage' baru
        # 'agent_node' berikutnya akan melihat ini dan merespons secara alami.
        await langgraph_agent.ainvoke(
            {"messages": [HumanMessage(content="Tidak, jangan lakukan itu.")]}, 
            config=config
        )
        
        return {"status": "tool_rejected", "message": "Eksekusi tool dibatalkan."}
        
    except Exception as e:
        logger.error(f"Gagal melanjutkan graph (reject_tool) untuk convo {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal melanjutkan graph: {e}"
        )