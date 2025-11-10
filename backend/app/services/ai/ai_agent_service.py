import logging
from typing import Dict, Any, AsyncGenerator, List
from pydantic import ValidationError

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.utils.function_calling import with_retry
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings #
from app.models.ai import AICanvasToolSchema
from app.models.block import BlockType #

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
    Ini adalah implementasi Fase 2.
    """
    
    def __init__(self):
        # 1. Inisialisasi Model (Gemini)
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_GENERATIVE_MODEL, #
            temperature=0.1,
            convert_system_message_to_human=True # Wajib untuk Gemini
        )
        
        # 2. Terapkan Retry (Solusi W4)
        # Jika API Gemini gagal, coba lagi 2x dengan backoff
        llm_with_retry = with_retry(
            llm,
            stop_after_attempt=3,
            wait_exponential_jitter=True,
            reraise=True # Lemparkan error jika retry gagal
        )
        
        # 3. Definisikan Tools
        self.tools = [create_block]
        
        # 4. Buat Prompt
        # (Prompt ini sangat penting untuk memaksa AI menggunakan tools)
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
        prompt_template = ChatPromptTemplate.from_template(prompt_str)
        
        # 5. Buat Agent
        agent = create_tool_calling_agent(llm_with_retry, self.tools, prompt_template)
        
        # 6. Buat Agent Executor
        self.agent_executor = AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            verbose=settings.DEBUG # Hanya verbose jika mode DEBUG
        )

    async def stream_agent_run(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Fungsi streaming utama (dipanggil oleh Fase 1).
        Ini menghasilkan (yield) 3 tipe event: 'status', 'tool_output', 'error'.
        """
        try:
            # Gunakan astream_events untuk mendapatkan log penuh
            async for event in self.agent_executor.astream_events(
                {"input": prompt, "chat_history": []},
                version="v1"
            ):
                kind = event["event"]
                
                if kind == "on_llm_start":
                    yield {"type": "status", "data": "AI: Berpikir..."}
                
                elif kind == "on_tool_start":
                    # Memberi feedback instan ke user
                    tool_name = event.get("name")
                    if tool_name == "create_block":
                        tool_input = event['data'].get('input', {})
                        block_type = tool_input.get('type', 'blok')
                        yield {"type": "status", "data": f"AI: Membuat {block_type}..."}
                
                elif kind == "on_tool_end":
                    # Ini adalah 'happy path'
                    # 'event['data']['input']' adalah dict yang dikirim ke tool
                    tool_input_dict = event['data'].get('input', {})
                    
                    try:
                        # (Solusi S1/W1) Validasi Pydantic
                        validated_block = AICanvasToolSchema.model_validate(tool_input_dict)
                        # Kirim payload yang bersih dan tervalidasi
                        yield {
                            "type": "tool_output", 
                            "data": validated_block.model_dump()
                        }
                    except ValidationError as e:
                        logger.warning(f"Validasi Pydantic gagal: {e}")
                        yield {
                            "type": "error", 
                            "data": f"AI Error: Model mengembalikan data tidak valid. {e}"
                        }
                
                elif kind == "on_llm_error" or kind == "on_tool_error":
                    # (Solusi W1/W4) Jika retry gagal
                    logger.error(f"Agent error stream: {event['data']}")
                    yield {
                        "type": "error", 
                        "data": f"AI Error: {event['data'].get('error', 'Gagal memproses.')}"
                    }

        except Exception as e:
            logger.error(f"Error kritis di stream_agent_run: {e}", exc_info=True)
            yield {
                "type": "error", 
                "data": f"Error Sistem: {e}"
            }

# --- Instance Singleton ---
# Kita buat satu instance untuk digunakan di seluruh aplikasi
ai_agent_service = AIAgentService()