import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING
from app.models.canvas import Canvas, PaginatedCanvasListResponse
from app.db.queries.canvas.canvas_queries import (
    get_canvases_in_workspace_paginated,
    get_user_personal_canvases_paginated
)

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

class CanvasListService:
    """
    Service untuk menangani logika bisnis terkait daftar Canvas.
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user = auth_info["user"]
        self.client = auth_info["client"]
        logger.debug(f"CanvasListService diinisialisasi untuk User: {self.user.id}")

    async def get_paginated_workspace_canvases(
        self, workspace_id: UUID, page: int, size: int
    ) -> PaginatedCanvasListResponse:
        """
        Mengambil daftar canvas workspace yang dipaginasi.
        """
        offset = (page - 1) * size
        logger.info(f"User {self.user.id} mengambil canvas workspace {workspace_id}: page {page}, size {size}")

        # Panggil kueri paginasi dari Langkah 2
        canvases_data, total = await asyncio.to_thread(
            get_canvases_in_workspace_paginated,
            self.client, workspace_id, offset, size
        )
        
        # Parse data mentah DB ke model Pydantic
        # Gunakan model_validate untuk menangani alias 'id'
        canvas_items = [Canvas.model_validate(c) for c in canvases_data]
        
        total_pages = (total + size - 1) // size
        
        return PaginatedCanvasListResponse(
            items=canvas_items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )

    async def get_paginated_personal_canvases(
        self, page: int, size: int
    ) -> PaginatedCanvasListResponse:
        """
        Mengambil daftar canvas pribadi yang dipaginasi.
        """
        offset = (page - 1) * size
        user_id = self.user.id
        logger.info(f"User {user_id} mengambil canvas pribadi: page {page}, size {size}")

        # Panggil kueri paginasi dari Langkah 2
        canvases_data, total = await asyncio.to_thread(
            get_user_personal_canvases_paginated,
            self.client, user_id, offset, size
        )
        
        canvas_items = [Canvas.model_validate(c) for c in canvases_data]
        total_pages = (total + size - 1) // size
        
        return PaginatedCanvasListResponse(
            items=canvas_items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )