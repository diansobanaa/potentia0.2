import logging
from typing import Dict, Any, AsyncGenerator, List, Optional  # <-- add Optional
from pydantic import ValidationError

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.utils.function_calling import with_retry
# from langchain_google_genai import ChatGoogleGenerativeAI  # <-- remove direct dependency

from app.core.config import settings
from app.models.ai import AICanvasToolSchema
from app.models.block import BlockType
from app.services.chat_engine.llm_provider import get_chat_model  # <-- use provider-agnostic factory

logger = logging.getLogger(__name__)

# --- Fase 2: Definisi Tools (S1/S4) ---
# Kita definisikan satu tool fleksibel yang divalidasi oleh Pydantic (S1)
# Ini adalah "bahasa" yang kita paksa AI untuk gunakan.

@tool(args_schema=AICanvasToolSchema)
def create_block(type: BlockType, content: str, properties: Optional[Dict[str, Any]] = None) -> str:
    """
    Gunakan tool ini untuk membuat SATU blok konten (seperti heading, 
    teks, atau list item) untuk canvas.
    """
    # Tool ini TIDAK menyimpan ke DB.
    # Ia hanya memvalidasi input dan mengembalikannya ke Agent Executor.
    block_type_str = type.value if isinstance(type, BlockType) else str(type)
    return f"Blok '{block_type_str}' dengan konten '{content[:30]}...' berhasil divalidasi."

# --- Service "Otak" AI ---

class AIAgentService:
    """
    Mengelola LangChain Agent dan Tool Calling.
    Stateless untuk pemilihan model LLM (frontend-driven).
    """
    
    def __init__(self):
        # Tools bersifat statis
        self.tools = [create_block]
        # Prompt statis
        prompt_str = """
        Anda adalah asisten penulis AI yang membantu pengguna di dalam 
        canvas kolaboratif.

        Tugas Anda adalah HANYA merespons menggunakan 'tools' yang 
        disediakan. JANGAN pernah merespons dengan teks biasa.

        Jika pengguna meminta sesuatu yang kompleks (misal: "5 ide..."), 
        panggil 'create_block' berulang kali untuk setiap bagian.
        
        Riwayat Obrolan:
        {chat_history}

        Permintaan Pengguna:
        {input}

        Alat yang tersedia:
        {agent_scratchpad}
        """
        self.prompt_template = ChatPromptTemplate.from_template(prompt_str)

    async def stream_agent_run(
        self,
        prompt: str,
        llm_config: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Fungsi streaming utama.
        - llm_config: {"model": "...", "temperature": 0.x, "max_tokens": N?}
        - chat_history: daftar pesan (opsional)
        """
        # Tentukan model/temperature per request (stateless)
        model = (llm_config or {}).get("model", settings.DEFAULT_MODEL)
        temperature = (llm_config or {}).get("temperature", settings.DEFAULT_TEMPERATURE)

        try:
            # Inisialisasi LLM per-call via factory (auto-detect provider dari nama model)
            base_llm = get_chat_model(model=model, temperature=temperature)
            llm_with_retry = with_retry(
                base_llm,
                stop_after_attempt=3,
                wait_exponential_jitter=True,
                reraise=True
            )

            # Buat agent & executor per-call (menghindari state lekat pada LLM)
            agent = create_tool_calling_agent(llm_with_retry, self.tools, self.prompt_template)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=settings.DEBUG
            )

            history = chat_history or []
            logger.info(f"AI Agent run with model={model}, temp={temperature}")

            async for event in agent_executor.astream_events(
                {"input": prompt, "chat_history": history},
                version="v1"
            ):
                kind = event["event"]

                if kind == "on_llm_start":
                    yield {"type": "status", "data": "AI: Berpikir..."}

                elif kind == "on_tool_start":
                    tool_name = event.get("name")
                    if tool_name == "create_block":
                        tool_input = event['data'].get('input', {})
                        block_type = tool_input.get('type', 'blok')
                        yield {"type": "status", "data": f"AI: Membuat {block_type}..."}

                elif kind == "on_tool_end":
                    tool_input_dict = event['data'].get('input', {})
                    try:
                        validated_block = AICanvasToolSchema.model_validate(tool_input_dict)
                        yield {
                            "type": "tool_output",
                            "data": validated_block.model_dump()
                        }
                    except ValidationError as e:
                        logger.warning(f"Validasi Pydantic gagal: {e}")
                        yield {"type": "error", "data": f"AI Error: Model mengembalikan data tidak valid. {e}"}

                elif kind in ("on_llm_error", "on_tool_error"):
                    logger.error(f"Agent error stream: {event['data']}")
                    yield {"type": "error", "data": f"AI Error: {event['data'].get('error', 'Gagal memproses.')}"}

        except Exception as e:
            logger.error(f"Error kritis di stream_agent_run: {e}", exc_info=True)
            yield {"type": "error", "data": f"Error Sistem: {e}"}

# --- Instance Singleton ---
# Kita buat satu instance untuk digunakan di seluruh aplikasi
ai_agent_service = AIAgentService()