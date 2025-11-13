# File: backend/app/services/chat_engine/tool_executor.py
# (File Baru - Fondasi Rencana v2.1)

import logging
import time
from typing import Dict, Any, Callable
from opentelemetry import trace
from prometheus_client import Counter, Histogram

from app.services.chat_engine.agent_state import AgentState

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# === Metrik Prometheus (Observability - Poin 2) ===
TOOL_CALLS_TOTAL = Counter(
    "tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "status"]
)
TOOL_CALL_LATENCY_SECONDS = Histogram(
    "tool_call_latency_seconds",
    "Latency of tool calls",
    ["tool_name"]
)

class ToolExecutor:
    """
    Wrapper terpusat untuk eksekusi tool yang aman.
    Mengimplementasikan NFR Poin 2 (Observability), 3 (Security), 
    5 (Idempotency), dan 12 (Wrapper).
    """

    def __init__(self, tool_registry: Dict[str, Callable]):
        """
        Args:
            tool_registry: Kamus (dict) yang memetakan nama tool ke 
                           fungsi async yang dapat dipanggil.
                           misal: {"create_schedule": calendar_tools.create_schedule_tool}
        """
        self.tools = tool_registry
        logger.info(f"ToolExecutor diinisialisasi dengan {len(self.tools)} tools.")

    async def aexecute_tool(self, state: AgentState, tool_call: Dict[str, Any]) -> Any:
        """
        Mengeksekusi satu tool call dengan aman.
        
        Args:
            state: AgentState saat ini.
            tool_call: Objek tool call (dari LLM atau pesan).

        Returns:
            Hasil dari eksekusi tool.
        """
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})

        if not tool_name or tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' tidak dikenal."
            TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="not_found").inc()
            logger.error(error_msg)
            return {"error": error_msg}

        # === Observability (Poin 2) ===
        with tracer.start_as_current_span(f"tool_call:{tool_name}") as span:
            start_time = time.time()
            span.set_attributes({
                "app.request_id": state.get("request_id"),
                "app.user_id": state.get("user_id"),
                "app.tool.name": tool_name,
                "app.tool.args": str(tool_args)
            })

            try:
                # === Keamanan (Poin 3): Pemeriksaan Izin ===
                required_permission = f"tool:{tool_name}"
                if required_permission not in state.get("permissions", []):
                    # Jika izin tidak ada, tolak eksekusi
                    raise PermissionError(
                        f"Izin ditolak untuk tool: '{tool_name}'. "
                        f"Pengguna tidak memiliki scope '{required_permission}'."
                    )

                # === Idempotency (Poin 5): Teruskan request_id ===
                # Kita asumsikan tool yang butuh idempotency (create_schedule)
                # akan menerima 'request_id' di dalam **kwargs.
                if "request_id" not in tool_args:
                    tool_args["request_id"] = state.get("request_id")
                
                # Dapatkan fungsi tool dari registry
                tool_function = self.tools[tool_name]
                
                # Eksekusi tool
                result = await tool_function(**tool_args)
                
                # === Observability (Poin 2) ===
                duration = time.time() - start_time
                TOOL_CALL_LATENCY_SECONDS.labels(tool_name=tool_name).observe(duration)
                TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="success").inc()
                span.set_status(trace.StatusCode.OK)
                
                return result

            except PermissionError as e:
                # Keamanan (Poin 3)
                duration = time.time() - start_time
                TOOL_CALL_LATENCY_SECONDS.labels(tool_name=tool_name).observe(duration)
                TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="permission_denied").inc()
                span.set_status(trace.StatusCode.ERROR, f"Permission denied: {e}")
                logger.warning(f"PERMISSION DENIED: {e}")
                return {"error": str(e)}

            except Exception as e:
                # Kegagalan Eksekusi (Poin 4 - Fallback)
                duration = time.time() - start_time
                TOOL_CALL_LATENCY_SECONDS.labels(tool_name=tool_name).observe(duration)
                TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="failed_exception").inc()
                span.set_status(trace.StatusCode.ERROR, f"Tool execution failed: {e}")
                logger.error(f"Eksekusi tool '{tool_name}' gagal: {e}", exc_info=True)
                return {"error": f"Eksekusi tool gagal: {e}"}