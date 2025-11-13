# File: backend/app/services/chat_engine/tools/external_tools.py
# (File Baru - Rencana v2.1 Fase 2)

import logging
from langchain_community.tools.tavily_search import TavilySearchResults
from app.core.config import settings

logger = logging.getLogger(__name__)

# Kita bungkus tool eksternal untuk keamanan dan standarisasi
# NFR Poin 3 (Keamanan): API key dikelola di server, tidak diekspos ke LLM.
try:
    if not settings.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY tidak diatur. Web search tool tidak akan berfungsi.")
        search_tool_instance = None
    else:
        # max_results=3 untuk efisiensi (NFR Poin 9)
        search_tool_instance = TavilySearchResults(
            max_results=3, 
            api_key=settings.TAVILY_API_KEY
        )
except ImportError:
    logger.error("Package 'tavily-python' tidak terinstal. Web search tool tidak akan berfungsi.")
    search_tool_instance = None
except Exception as e:
    logger.error(f"Gagal menginisialisasi TavilySearch: {e}")
    search_tool_instance = None

async def search_online(query: str, request_id: str) -> str:
    """
    Tool untuk melakukan pencarian web.
    Menerima request_id untuk tracing (NFR Poin 5).
    """
    logger.info(f"REQUEST_ID: {request_id} - Tool 'search_online' dipanggil dengan kueri: {query}")
    if not search_tool_instance:
        return "Error: Layanan pencarian web tidak dikonfigurasi di server."
        
    try:
        # .ainvoke() adalah metode async dari tool LangChain
        result = await search_tool_instance.ainvoke(query)
        return result
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Error saat eksekusi search_online: {e}", exc_info=True)
        return f"Error: Gagal melakukan pencarian web. {e}"