# File: backend/app/services/chat_engine/llm_client.py
# (File Baru - Fondasi Rencana v2.1)

import logging
import time
import tiktoken
tiktoken.get_encoding("cl100k_base")
from typing import List, Optional
from opentelemetry import trace
from prometheus_client import Counter, Histogram
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from app.core.config import settings
from app.services.chat_engine.agent_state import AgentState

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# === Metrik Prometheus (Observability - Poin 2) ===
LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
    ["model", "outcome"]
)
LLM_CALL_LATENCY_SECONDS = Histogram(
    "llm_call_latency_seconds",
    "Latency of LLM calls",
    ["model"]
)

class LLMClient:
    """
    Wrapper terpusat untuk semua panggilan LLM.
    Mengimplementasikan NFR Poin 2 (Observability), 4 (Reliability), 
    8 (Cost), dan 12 (Wrapper).
    """

    def __init__(self, model_name: str, temperature: float = 0.1, timeout: int = 60):
        self.model_name = model_name
        self.timeout_seconds = timeout
        
        try:
            self.tokenizer = tiktoken.get_encoding("cl10k_base")
        except Exception:
            logger.warning("Tiktoken (cl10k_base) tidak ditemukan. Estimasi token tidak akan akurat.")
            self.tokenizer = None

        # Inisialisasi LLM Client
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True
        )

    def get_llm(self) -> ChatGoogleGenerativeAI:
        """Mengembalikan instance LangChain LLM yang mendasarinya."""
        return self.llm

    def _count_tokens(self, text: str) -> int:
        """Menghitung token menggunakan tiktoken (Poin 8)."""
        if not self.tokenizer:
            return len(text) // 4  # Estimasi kasar
        return len(self.tokenizer.encode(text))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def ainvoke(
        self,
        messages: List[BaseMessage],
        state: Optional[AgentState] = None
    ) -> LLMResult:
        """
        Mengeksekusi panggilan LLM dengan Reliability & Observability.
        
        Args:
            messages: Daftar pesan untuk dikirim ke LLM.
            state: AgentState (opsional) untuk tracing dan estimasi biaya.

        Returns:
            LLMResult dari LangChain.
        """
        model_label = self.model_name.replace("-latest", "")
        span_name = f"llm_call:{model_label}"
        
        # === Observability (Poin 2) ===
        with tracer.start_as_current_span(span_name) as span:
            start_time = time.time()
            if state:
                span.set_attributes({
                    "app.request_id": state.get("request_id"),
                    "app.user_id": state.get("user_id"),
                    "app.trace_id": state.get("trace_id"),
                })

            try:
                # Estimasi Token Input (Poin 8)
                input_tokens = sum(self._count_tokens(msg.content) for msg in messages)
                span.set_attribute("llm.input_tokens", input_tokens)

                # === Reliability (Poin 4) ===
                result = await self.llm.agenerate(
                    [messages], 
                    timeout=self.timeout_seconds
                )
                
                duration = time.time() - start_time
                
                # Estimasi Token Output & Biaya (Poin 8)
                output_tokens = 0
                if result.generations:
                    output_text = result.generations[0][0].text
                    output_tokens = self._count_tokens(output_text)
                
                # (TODO: Implementasi logika estimasi biaya di sini jika diperlukan)
                # cost = calculate_cost(input_tokens, output_tokens, self.model_name)
                # if state:
                #     state["cost_estimate"] += cost

                # === Observability (Poin 2) ===
                LLM_CALL_LATENCY_SECONDS.labels(model=model_label).observe(duration)
                LLM_CALLS_TOTAL.labels(model=model_label, outcome="success").inc()
                span.set_attributes({
                    "llm.output_tokens": output_tokens,
                    "llm.total_tokens": input_tokens + output_tokens,
                    # "llm.cost": cost
                })
                span.set_status(trace.StatusCode.OK)
                
                return result

            except RetryError as e:
                # Gagal setelah semua retry
                duration = time.time() - start_time
                LLM_CALL_LATENCY_SECONDS.labels(model=model_label).observe(duration)
                LLM_CALLS_TOTAL.labels(model=model_label, outcome="failed_retry").inc()
                span.set_status(trace.StatusCode.ERROR, f"LLM call failed after retries: {e}")
                logger.error(f"LLM call gagal setelah retries: {e}")
                raise  # Lemparkan kembali error
                
            except Exception as e:
                # Gagal pada percobaan pertama (atau error non-retryable)
                duration = time.time() - start_time
                LLM_CALL_LATENCY_SECONDS.labels(model=model_label).observe(duration)
                LLM_CALLS_TOTAL.labels(model=model_label, outcome="failed_exception").inc()
                span.set_status(trace.StatusCode.ERROR, f"LLM call exception: {e}")
                logger.error(f"LLM call exception: {e}")
                raise

# --- Contoh Inisialisasi Klien (Akan digunakan oleh graph) ---
llm_flash_client = LLMClient(model_name=settings.GEMINI_RERANKER_MODEL, temperature=0.0)
llm_pro_client = LLMClient(model_name=settings.GEMINI_GENERATIVE_MODEL, temperature=0.2)
