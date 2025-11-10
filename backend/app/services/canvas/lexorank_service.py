# File: backend/services/canvas/lexorank_service.py
# (DIREFACTOR TOTAL - Mengganti float logic dengan Base-62 (Jira-style))

import logging
import asyncio
from typing import Optional, List
from uuid import UUID
import json
import redis.asyncio as redis

from app.core.config import settings #
from app.db.supabase_client import get_supabase_admin_async_client
from app.core.exceptions import DatabaseError

# Impor file query DB yang telah kita buat
from app.db.queries.canvas import block_queries

logger = logging.getLogger(__name__)

# --- [BARU] Logika Base-62 untuk LexoRank ---
# (Menggantikan _extract_number, _increment, _decrement, _between dari file lama)

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CHARSET_MAP = {char: i for i, char in enumerate(CHARSET)}
MIN_CHAR = CHARSET[0]  # '0'
MAX_CHAR = CHARSET[-1]  # 'z'
MID_CHAR = CHARSET[len(CHARSET) // 2] # 'U'

class LexoRankService:
    """
    Service untuk mengelola LexoRank pada block di canvas.
    (Sekarang menggunakan algoritma base-62 yang efisien)
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def _get_admin_client(self):
        """Helper untuk mendapatkan admin client."""
        return await get_supabase_admin_async_client()

    def _increment(self, prev: str) -> str:
        """[BARU] Menghasilkan string berikutnya dalam urutan base-62."""
        if not prev:
            return MID_CHAR # Basis kasus
            
        last_char = prev[-1]
        
        if last_char != MAX_CHAR:
            # Kasus mudah: 'a' -> 'b'
            idx = CHARSET_MAP[last_char]
            return prev[:-1] + CHARSET[idx + 1]
        
        # Kasus rekursif: 'az' -> 'b0'
        return self._increment(prev[:-1]) + MIN_CHAR

    def _decrement(self, next_str: str) -> str:
        """[BARU] Menghasilkan string sebelumnya dalam urutan base-62."""
        if not next_str:
            return MID_CHAR # Basis kasus

        last_char = next_str[-1]
        
        if last_char != MIN_CHAR:
            # Kasus mudah: 'b' -> 'a'
            idx = CHARSET_MAP[last_char]
            return next_str[:-1] + CHARSET[idx - 1]
        
        # Kasus rekursif: 'b0' -> 'az'
        return self._decrement(next_str[:-1]) + MAX_CHAR

    def _between(self, prev: Optional[str], next_str: Optional[str]) -> str:
        """[BARU] Menghasilkan string di antara dua string (base-62)."""
        
        # 1. Kasus Sederhana (di awal atau akhir)
        if prev is None or prev == "":
            if next_str is None or next_str == "": return MID_CHAR
            return self._decrement(next_str) # Tempatkan sebelum 'next'
            
        if next_str is None or next_str == "":
            return self._increment(prev) # Tempatkan setelah 'prev'

        # 2. Kasus Kompleks (di tengah)
        mid_str = ""
        i = 0
        while True:
            prev_char = prev[i] if i < len(prev) else MIN_CHAR
            next_char = next_str[i] if i < len(next_str) else MAX_CHAR
            
            if prev_char == next_char:
                # 'abc' dan 'abd' -> 'abc'
                mid_str += prev_char
                i += 1
                continue
                
            prev_idx = CHARSET_MAP[prev_char]
            next_idx = CHARSET_MAP[next_char]
            
            if next_idx - prev_idx > 1:
                # 'a' dan 'c' -> 'b' (selesai)
                mid_idx = (prev_idx + next_idx) // 2
                return mid_str + CHARSET[mid_idx]
            
            # 'a' dan 'b' -> 'a...'
            mid_str += prev_char
            
            # Recurse: cari di antara 'a...' dan 'b...'
            # Ini menjadi _between(sisa_dari_prev, None)
            # yang akan memanggil _increment(sisa_dari_prev)
            return mid_str + self._increment(prev[i+1:] if i + 1 < len(prev) else None)

    async def generate_order(
        self, 
        canvas_id: UUID, 
        parent_id: Optional[UUID] = None, 
        position: str = "end"
    ) -> str:
        """
        Menghasilkan LexoRank baru untuk block.
        (Logika orkestrasi ini tidak berubah)
        """
        try:
            admin_client = await self._get_admin_client()
            
            siblings = await block_queries.get_sibling_blocks_db(
                admin_client, canvas_id, parent_id
            )
            
            if not siblings:
                return MID_CHAR # [PERBAIKAN] Gunakan MID_CHAR, bukan 'a0'
            
            if position == "start":
                first_order = siblings[0]["y_order"]
                return self._between(None, first_order)
            
            elif position.startswith("after:"):
                after_block_id = position.split(":", 1)[1]
                
                after_order = None
                for i, block in enumerate(siblings):
                    if str(block["block_id"]) == after_block_id:
                        after_order = block["y_order"]
                        next_order = None
                        if i + 1 < len(siblings):
                            next_order = siblings[i + 1]["y_order"]
                        
                        return self._between(after_order, next_order)
                
                last_order = siblings[-1]["y_order"]
                return self._between(last_order, None)
            
            else:  # position == "end"
                last_order = siblings[-1]["y_order"]
                return self._between(last_order, None)
                
        except (Exception, DatabaseError) as e:
            logger.error(f"Error generating order: {e}", exc_info=True)
            return f"z{int(asyncio.get_event_loop().time())}" # Fallback
    
    async def check_rebalance_needed(self, canvas_id: UUID):
        """
        Memberi notifikasi ke Redis bahwa rebalancing diperlukan.
        (Tidak berubah)
        """
        try:
            # Perhatikan: Ini mendorong ke REDIS.
            # Pastikan RebalanceWorker Anda mendengarkan pg_notify
            # DAN juga antrian fallback ini, atau ubah ini.
            #
            # Sesuai blueprint, trigger DB sudah
            # menangani 'pg_notify'. Kita hapus ini agar tidak membingungkan.
            logger.debug(f"Pengecekan rebalance dilewati, ditangani oleh trigger DB.")
            pass
            
        except Exception as e:
            logger.error(f"Error notifying rebalance needed: {e}", exc_info=True)
    
    async def rebalance(self, canvas_id: UUID):
        """
        Melakukan rebalancing LexoRank untuk canvas.
        (Logika orkestrasi tidak berubah)
        """
        try:
            admin_client = await self._get_admin_client()
            
            blocks = await block_queries.get_all_blocks_for_rebalance_db(
                admin_client, canvas_id
            )
            
            if not blocks:
                logger.info(f"Tidak ada block untuk rebalance di canvas {canvas_id}")
                return

            blocks_by_parent = {}
            for block in blocks:
                parent_id = block.get("parent_id")
                if parent_id not in blocks_by_parent:
                    blocks_by_parent[parent_id] = []
                blocks_by_parent[parent_id].append(block)
            
            update_tasks = []
            
            for parent_id, parent_blocks in blocks_by_parent.items():
                # [PERBAIKAN] Gunakan generator base-62
                new_orders = self._generate_new_orders(len(parent_blocks))
                
                for i, block in enumerate(parent_blocks):
                    task = block_queries.update_block_y_order_db(
                        admin_client, block["block_id"], new_orders[i]
                    )
                    update_tasks.append(task)
            
            await asyncio.gather(*update_tasks)
            
            logger.info(f"Rebalanced canvas {canvas_id} sukses ({len(update_tasks)} blocks).")
            
        except (Exception, DatabaseError) as e:
            logger.error(f"Error rebalancing canvas {canvas_id}: {e}", exc_info=True)
    
    def _generate_new_orders(self, count: int) -> List[str]:
        """
        [BARU] Menghasilkan list order baru yang tersebar (base-62).
        Ini menghasilkan 'U', 'V', 'W' ... (jika < 62)
        atau 'U0', 'U1', 'U2' ... (jika > 62)
        """
        if count == 0:
            return []
        
        if count <= len(CHARSET):
            # Jika sedikit, sebar di seluruh charset
            step = len(CHARSET) // (count + 1)
            return [CHARSET[i * step] for i in range(1, count + 1)]
        else:
            # Jika banyak, gunakan 2 karakter
            prefix = MID_CHAR
            max_per_prefix = len(CHARSET)
            if count > max_per_prefix * max_per_prefix:
                logger.warning(f"Terlalu banyak item ({count}) untuk rebalance 2-char.")
                # Fallback ke 3 char
                return [f"{prefix}{CHARSET[i // max_per_prefix % max_per_prefix]}{CHARSET[i % max_per_prefix]}" for i in range(count)]
            
            return [f"{prefix}{CHARSET[i % max_per_prefix]}" for i in range(count)] 