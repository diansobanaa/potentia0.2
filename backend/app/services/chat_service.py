# File: backend/app/services/chat_service.py
# (Diperbarui untuk AsyncClient native penuh dan Perbaikan SyntaxError)

import logging
import asyncio
import re
import json
import tiktoken
from uuid import UUID
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel
from fastapi import BackgroundTasks

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from app.core.config import settings
from app.core.dependencies import AuthInfoDep, EmbeddingServiceDep, JudgeChainDep 
from app.models.user import User
from app.core.exceptions import DatabaseError, NotFoundError

from app.services.chat_engine.schemas import (
    ChatRequest, ChatResponse, JudgeDecision, 
    AIResponseStructured, ExtractedPreference, PreferenceItem
)
from app.prompts import ai_judge_prompt_templates as judge_prompts
from app.prompts.assessor_prompt import JSON_ASSESSOR_PROMPT_TEMPLATE

from app.services.chat_engine.context_manager import ContextManager
from app.services.chat_engine.user_preference_memory_service import save_preferences_to_db
from app.db.queries.conversation import (
    context_queries, 
    log_queries, 
    conversation_queries, 
    message_queries
)
from app.services.chat_engine.context_packer import ContextPacker
from app.services.chat_engine.llm_chat_executor import LLMExecutor

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable 
    from app.services.embedding_service import EmbeddingService
    from supabase.client import AsyncClient

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKEN_BUDGET = 6144
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception:
    logger.warning("Gagal memuat tiktoken, beralih ke estimasi split()")
    TOKENIZER = None

class ChatService:
    def __init__(
        self, 
        auth_info: AuthInfoDep, 
        embedding_service: EmbeddingServiceDep, 
        judge_chain: JudgeChainDep
    ):
        self.user: User = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] 
        self.embedding_service: 'EmbeddingService' = embedding_service
        self.judge_chain: 'Runnable' = judge_chain
        self.context_manager = ContextManager(self.client, self.user)
        self.specialist_executor = LLMExecutor() 
        
        self.assessor_llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_ASESOR_MODEL, 
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )
        self.assessor_parser = PydanticOutputParser(pydantic_object=ExtractedPreference)
        self.assessor_prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{assessor_prompt}\n\n{format_instructions}"),
            ("human", "PESAN ASLI PENGGUNA:\n{original_user_query}") 
        ])
        self.assessor_chain = self.assessor_prompt_template | self.assessor_llm | self.assessor_parser
        
        self.context_packer = ContextPacker(self.client, self.embedding_service)
        logger.debug(f"ChatService (Async) diinisialisasi untuk User: {self.user.id}")

    def _format_summaries(self, summaries: List[dict]) -> str:
        return judge_prompts.format_retrieved_summaries(summaries)
    
    def _format_decision_history(self, decisions: List[dict]) -> str:
        return judge_prompts.format_decision_history(decisions)

    # --- [PERBAIKAN SYNTAXERROR] ---
    # Mengganti '...' dengan argumen fungsi yang sebenarnya
    
    async def _handle_new_context_flow(
        self, 
        conversation_id: UUID, 
        judge_decision: JudgeDecision,
        user_message: str # (user_message diganti namanya dari requeried_prompt agar cocok)
    ) -> Dict[str, Any]:
        logger.info(f"Mengeksekusi alur NEW untuk convo {conversation_id}.")
        # (Gunakan user_message yang diteruskan, yang merupakan requeried_prompt)
        new_context = await self.context_manager.create_new_chat_session(
            conversation_id, 
            initial_summary=f"Konteks baru tentang: {user_message[:50]}..."
        )
        return new_context
 
    async def _handle_continue_flow(
        self, 
        context: Dict[str, Any], 
        judge_decision: JudgeDecision,
        user_message: str
    ) -> Dict[str, Any]:
        logger.info(f"Mengeksekusi alur CONTINUE pada konteks {context['context_id']}.")
        return context

    async def _handle_switch_flow(
        self, 
        conversation_id: UUID,
        judge_decision: JudgeDecision,
        user_message: str
    ) -> Dict[str, Any]:
        summary_id = judge_decision.chosen_summary_id
        logger.info(f"Mengeksekusi alur SWITCH ke summary {summary_id}.")
        if not summary_id:
             raise DatabaseError("Decision 'Switch' tanpa chosen_summary_id.")
        switched_context, _ = await self.context_manager.load_switched_context(summary_id)
        return switched_context
    # --- [AKHIR PERBAIKAN SYNTAXERROR] ---

    def _parse_specialist_output(self, raw_text_output: str) -> Tuple[str, str]:
        thinking_log = "LLM tidak menghasilkan reasoning (parsing gagal)."
        ai_response_text = raw_text_output.strip() 
        try:
            match = re.search(r"<thinking>(.*?)</thinking>", raw_text_output, re.DOTALL | re.IGNORECASE)
            if match:
                thinking_log = match.group(1).strip()
                ai_response_text = raw_text_output[match.end():].strip()
                if not ai_response_text:
                    ai_response_text = "Maaf, saya selesai berpikir tetapi gagal menghasilkan respons. Silakan coba lagi."
            else:
                thinking_log = "[PERINGATAN] AI (P#2) gagal menghasilkan blok <thinking>."
                ai_response_text = raw_text_output.strip()
        except Exception as e:
            logger.error(f"Error saat parsing Regex V6: {e}", exc_info=True)
            thinking_log = f"[ERROR] Gagal parsing Regex: {e}"
        return thinking_log, ai_response_text

    async def _run_assessor_call(
        self, 
        original_user_query: str
    ) -> ExtractedPreference:
        logger.info("Memulai Panggilan #3 (Asesor)...")
        try:
            extracted_data = await self.assessor_chain.ainvoke({
                "assessor_prompt": JSON_ASSESSOR_PROMPT_TEMPLATE, 
                "format_instructions": self.assessor_parser.get_format_instructions(),
                "original_user_query": original_user_query or "(tidak ada input)"
            })
            logger.info("✅ Panggilan #3 (Asesor) berhasil mengekstrak JSON preferensi.")
            return extracted_data
        except OutputParserException as e:
            logger.error(f"❌ Gagal Panggilan #3 (Asesor) - OutputParserException: {e}", exc_info=True)
            return ExtractedPreference(preferences=[])
        except Exception as e:
            logger.error(f"❌ Gagal Panggilan #3 (Asesor) - Error tidak terduga: {e}", exc_info=True)
            return ExtractedPreference(preferences=[])


    async def handle_chat_turn_full_pipeline(
            self, 
            request: ChatRequest,
            background_tasks: BackgroundTasks
        ) -> ChatResponse:
        
        logger.info(f"Memulai pipeline chat (Async) untuk User {self.user.id}...")
        
        judge_decision: Optional[JudgeDecision] = None
        final_context: Optional[Dict[str, Any]] = None
        user_message_db: Optional[Dict[str, Any]] = None
        user_message = request.message or "(tidak ada input)"
        
        ai_response = "Maaf, saya tidak dapat memberikan jawaban saat ini."
        thinking_log = "LLM tidak menghasilkan reasoning."
        preferences_list_final = []
        
        try:
            conversation_id: Optional[UUID] = request.conversation_id
            active_context: Optional[Dict[str, Any]] = None
            history_messages: List[Dict[str, Any]] = []

            # (Panggilan 'get_or_create_conversation' dan 'load_memory_for_judge'
            #  sekarang async native)
            if conversation_id:
                logger.info(f"Melanjutkan thread yang ada: {conversation_id}")
                conversation = await conversation_queries.get_or_create_conversation(
                    self.client, self.user.id, conversation_id
                )
                (active_context, history_messages) = await self.context_manager.load_memory_for_judge(
                    conversation_id, request.context_id 
                )
            else:
                logger.info("Memulai thread baru (conversation_id adalah null).")
                conversation = await conversation_queries.get_or_create_conversation(
                    self.client, self.user.id, None
                )
                conversation_id = conversation['conversation_id']
                active_context = {} 
                history_messages = [] 
            
            # (Panggilan 'generate_embedding' sudah async native)
            prompt_embedding = await self.embedding_service.generate_embedding(
                text=user_message or "", task_type="retrieval_query"
            )
            
            # (Panggilan 'find_relevant_summaries' dan 'get_recent_decisions'
            #  sekarang async native)
            retrieved_summaries, decision_history_data = await asyncio.gather(
                context_queries.find_relevant_summaries(
                    self.client, self.user.id, prompt_embedding
                ),
                log_queries.get_recent_decisions(
                    self.client, self.user.id, conversation_id, limit=5
                )
            )
            
            # (Logika format prompt tidak berubah)
            current_summary_text = active_context.get("summary", [{}])[0].get("summary_text", "Tidak ada.") if active_context else "Tidak ada."
            retrieved_summaries_text = self._format_summaries(retrieved_summaries)
            decision_history_text = self._format_decision_history(decision_history_data)
            try: last_user_prompt = next(msg['content'] for msg in history_messages if msg.get('role') == 'user')
            except StopIteration: last_user_prompt = "Tidak ada balasan sebelumnya."
            try: last_ai_response = next(msg['content'] for msg in history_messages if msg.get('role') == 'assistant')
            except StopIteration: last_ai_response = "Tidak ada balasan AI sebelumnya."
            context_data_dict = {
                "current_summary": current_summary_text or "",
                "current_history": history_messages or "",
                "last_user_prompt": last_user_prompt or "",
                "last_ai_response": last_ai_response or "",
                "last_decisions": decision_history_text or "",
                "retrieved_summaries": retrieved_summaries_text or "",
                "input": user_message
            }
            formatted_context_judge = judge_prompts.CONTEXT_DATA_TEMPLATE.format(**context_data_dict)
            final_judge_prompt = judge_prompts.JUDGE_SYSTEM_INSTRUCTION.format(context_data=formatted_context_judge)
            
            # (Panggilan Judge chain sudah async)
            logger.warning(f"--- MENGIRIM PROMPT N52 KE LLM JUDGE (P#1) ---")
            raw_result = await self.judge_chain.ainvoke(final_judge_prompt)
            judge_dict = json.loads(raw_result)
            judge_decision = JudgeDecision(**judge_dict)
            logger.info(f"Keputusan Judge Diterima: {judge_decision.context_assessment} | Ambiguous: {judge_decision.is_ambiguous}")

            # (Panggilan helper strategi sudah async)
            final_context = active_context
            requeried_prompt = judge_decision.requeried_prompt if (judge_decision.requeried_prompt and judge_decision.requeried_prompt.strip()) else user_message
            
            if judge_decision.context_assessment == "New":
                final_context = await self._handle_new_context_flow(conversation_id, judge_decision, requeried_prompt)
            elif judge_decision.context_assessment == "Switch":
                final_context = await self._handle_switch_flow(conversation_id, judge_decision, requeried_prompt)
            elif judge_decision.context_assessment == "Continue" and final_context:
                final_context = await self._handle_continue_flow(final_context, judge_decision, requeried_prompt)
            else:
                final_context = await self._handle_new_context_flow(conversation_id, judge_decision, requeried_prompt)
            
            context_id = final_context.get("context_id") if final_context else None

            if not judge_decision.is_ambiguous:
                system_prompt_v6 = self.specialist_executor._build_system_prompt(
                    judge_decision.context_assessment or "New",
                    bool(active_context)
                )
                
                # (Panggilan ContextPacker sudah async native penuh)
                final_context_for_specialist = await self.context_packer.build_context(
                    user_id=self.user.id,
                    system_prompt=system_prompt_v6,
                    requeried_prompt=requeried_prompt,
                    original_user_query=user_message,
                    history_messages=history_messages, 
                    current_summary=current_summary_text
                )

                # (Eksekusi Paralel sudah async)
                logger.info("🚀 Memulai Panggilan #2 (Spesialis) dan Panggilan #3 (Asesor) secara paralel...")
                try:
                    (specialist_raw_output, assessor_response) = await asyncio.gather(
                        self.specialist_executor.run_final_prompt(
                            system_prompt=system_prompt_v6,
                            requeried_query=requeried_prompt,
                            original_user_query=user_message,
                            formatted_context=final_context_for_specialist,
                            context_strategy=judge_decision.context_assessment
                        ),
                        self._run_assessor_call(
                            original_user_query=user_message
                        )
                    )
                    
                    thinking_log, ai_response = self._parse_specialist_output(specialist_raw_output)

                    if assessor_response and hasattr(assessor_response, "preferences"):
                        preferences_list_final = [p.model_dump() for p in assessor_response.preferences]
                    
                except Exception as model_err:
                    logger.error(f"❌ Gagal saat menjalankan P#2 atau P#3: {model_err}", exc_info=True)
            
            else: # Jika ambigu
                ai_response = judge_decision.clarification_question or "Maaf, saya kurang mengerti. Bisa diperjelas?"
                thinking_log = "Ambiguitas terdeteksi. Meminta klarifikasi."

            # 7. LOG & SIMPAN (Async Native)
            if preferences_list_final:
                background_tasks.add_task(
                    save_preferences_to_db,
                    authed_client=self.client,
                    embedding_service=self.embedding_service,
                    user_id=self.user.id,
                    preferences_list=preferences_list_final
                )
            
            user_message_db = None
            try:
                logger.info("📜 Menyimpan Data Message (Async)...")
                # (Panggilan 'save_turn_messages' sekarang async native)
                user_message_db = await message_queries.save_turn_messages(
                    self.client, self.user.id, conversation_id, context_id,
                    user_message, ai_response
                )
                logger.info("✅ Data message berhasil disimpan ke database.")
            except Exception as log_err:
                logger.error(f"❌ Gagal menyimpan Data Message: {log_err}", exc_info=True)

            try:
                # (Panggilan 'create_decision_log_safe' sekarang async native)
                await log_queries.create_decision_log_safe(
                    self.client, self.user.id, conversation_id,
                    user_message_db.get("message_id") if user_message_db else None,
                    context_id, judge_decision.reason,
                    judge_decision.model_dump(mode="json"),
                )
                logger.info("✅ Log keputusan berhasil disimpan ke tabel decision_logs.")
            except Exception as log_err:
                logger.error(f"❌ Gagal menyimpan log keputusan: {log_err}", exc_info=True)

            # 10. KEMBALIKAN RESPONS AKHIR
            return ChatResponse(
                ai_response=ai_response,
                thinking=thinking_log,
                conversation_id=conversation_id,
                context_id=context_id,
                # --- PERBAIKAN: Gunakan 'self.user.id' ---
                user_id=self.user.id, 
                user_message=user_message,
                judge_decision=judge_decision.model_dump(mode="json"),
                extracted_user_preferences=preferences_list_final,
            )

        except Exception as e:
            logger.error(f"Gagal mengeksekusi pipeline chat penuh: {e}", exc_info=True)
            reason = getattr(judge_decision, 'reason', 'Error sebelum Juri selesai.')
            raise DatabaseError(f"Gagal mengeksekusi pipeline chat penuh: {str(e)} | Alasan Juri: {reason}")