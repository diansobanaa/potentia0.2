# File: backend/app/db/queries/workspace/workspace_list.py
# List dan paginasi operations untuk Workspace

import logging
import asyncio
from typing import List, Dict, Any, Tuple
from uuid import UUID
from supabase.client import AsyncClient

logger = logging.getLogger(__name__)


async def get_user_workspaces_paginated(
    authed_client: AsyncClient,
    user_id: UUID,
    offset: int,
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (Async Native) Mengambil daftar workspace dengan paginasi.

    Menggunakan asyncio.gather untuk menjalankan query list dan count
    secara paralel untuk optimasi performa.
    """
    try:
        # Query 1: Ambil data paginasi
        list_task = authed_client.table("workspace_members") \
            .select("Workspaces(*)") \
            .eq("user_id", str(user_id)) \
            .order("workspace_id", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # Query 2: Ambil total hitungan (count)
        count_task = authed_client.table("workspace_members") \
            .select("workspace_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .execute()

        # Jalankan kueri secara paralel
        list_response, count_response = await asyncio.gather(
            list_task,
            count_task
        )

        data = getattr(list_response, "data", None) or []
        total = getattr(count_response, "count", 0) or 0

        workspaces = [
            item["workspaces"] for item in data if item.get("workspaces")
        ]
        return workspaces, total
    except Exception as e:
        logger.error(
            f"Error paginating user workspaces (async): {e}",
            exc_info=True
        )
        return [], 0  # Kembalikan list kosong saat error

