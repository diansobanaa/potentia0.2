"""
Lightweight observability collector for LLM call tracking.
Stores data in-memory for real-time debugging (not persisted).
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class LLMCallTrace:
    """Single LLM call trace."""
    node_name: str
    model: str
    temperature: float
    prompt_messages: List[Dict[str, any]]  # [{role, tokens, content_preview}]
    input_tokens: int
    output_tokens: int
    duration_ms: float
    cost_usd: float
    timestamp: str
    error: Optional[str] = None


@dataclass
class RequestTrace:
    """Full request trace (all LLM calls in one chat request)."""
    request_id: str
    conversation_id: str
    user_message: str
    llm_calls: List[LLMCallTrace] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def add_llm_call(self, call: LLMCallTrace):
        """Add LLM call and update totals."""
        self.llm_calls.append(call)
        self.total_input_tokens += call.input_tokens
        self.total_output_tokens += call.output_tokens
        self.total_cost_usd += call.cost_usd
        self.total_duration_ms += call.duration_ms
        if call.error:
            self.errors.append(f"[{call.node_name}] {call.error}")
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "user_message": self.user_message,
            "llm_calls": [asdict(call) for call in self.llm_calls],
            "summary": {
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_cost_usd": round(self.total_cost_usd, 6),
                "total_duration_ms": round(self.total_duration_ms, 2),
                "num_llm_calls": len(self.llm_calls),
                "errors": self.errors
            }
        }


class ObservabilityCollector:
    """
    In-memory collector for LLM call traces.
    Not persisted - only for real-time debugging.
    """
    
    # Class-level storage (shared across requests)
    _active_traces: Dict[str, RequestTrace] = {}
    
    # Pricing (Gemini Flash - update sesuai model Anda)
    PRICING = {
        "gemini-flash-lite-latest": {
            "input": 0.000035 / 1000,   # $0.000035 per 1K tokens
            "output": 0.00014 / 1000    # $0.00014 per 1K tokens
        },
        "gemini-2.0-flash-exp": {
            "input": 0.000035 / 1000,
            "output": 0.00014 / 1000
        }
    }
    
    @classmethod
    def start_request(cls, request_id: str, conversation_id: str, user_message: str):
        """Start tracking a new request."""
        cls._active_traces[request_id] = RequestTrace(
            request_id=request_id,
            conversation_id=conversation_id,
            user_message=user_message
        )
    
    @classmethod
    def add_llm_call(
        cls,
        request_id: str,
        node_name: str,
        model: str,
        temperature: float,
        prompt_messages: List[Dict],
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """Record an LLM call."""
        if request_id not in cls._active_traces:
            return
        
        # Calculate cost
        pricing = cls.PRICING.get(model, cls.PRICING["gemini-flash-lite-latest"])
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        
        call = LLMCallTrace(
            node_name=node_name,
            model=model,
            temperature=temperature,
            prompt_messages=prompt_messages,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            cost_usd=cost,
            timestamp=datetime.utcnow().isoformat(),
            error=error
        )
        
        cls._active_traces[request_id].add_llm_call(call)
    
    @classmethod
    def get_trace(cls, request_id: str) -> Optional[RequestTrace]:
        """Get trace for a request."""
        return cls._active_traces.get(request_id)
    
    @classmethod
    def finalize_request(cls, request_id: str) -> Optional[dict]:
        """Finalize and return trace, then remove from memory."""
        trace = cls._active_traces.pop(request_id, None)
        return trace.to_dict() if trace else None
