# File: backend/app/services/calendar/subscription_service.py
# (File ini SUDAH BENAR, tidak perlu diubah)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING, Optional
from supabase.client import AsyncClient
from app.models.user import User
from app.models.schedule import SubscriptionRole, SubscriptionCreate
from app.db.queries.calendar import calendar_queries
from app.core.exceptions import DatabaseError, NotFoundError
from app.services.audit_service import log_action

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

class SubscriptionService:
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"]
        logger.debug(f"SubscriptionService (Async) diinisialisasi untuk User: {self.user.id}")

    async def create_new_subscription(
        self, 
        calendar_id: UUID,
        payload: SubscriptionCreate
    ) -> Dict[str, Any]:
        
        existing_sub = await calendar_queries.get_user_subscription(
            self.client, payload.user_id, calendar_id
        )
        if existing_sub:
            raise DatabaseError("invite_conflict", "Pengguna sudah berlangganan ke kalender ini.")

        try:
            new_subscription = await calendar_queries.create_subscription(
                self.client,
                payload.user_id,
                calendar_id,
                payload.role
            )
            
            # --- Panggilan ini SUDAH BENAR menggunakan 'await' ---
            await log_action(
                user_id=self.user.id,
                action="calendar.subscription_create",
                details={
                    "subscription_id": str(new_subscription['subscription_id']),
                    "calendar_id": str(calendar_id),
                    "target_user_id": str(payload.user_id),
                    "role_granted": payload.role.value
                }
            )
            # ---------------------------------------------
            
            return new_subscription
        except Exception as e:
            # (Error handling tidak berubah)
            if "invite_conflict" in str(e) or "unique_user_calendar_subscription" in str(e):
                 raise DatabaseError("invite_conflict", "Pengguna sudah berlangganan.")
            if isinstance(e, DatabaseError): raise
            raise DatabaseError("create_subscription_service", str(e))

    async def get_calendar_subscriptions(self, calendar_id: UUID) -> List[Dict[str, Any]]:
        try:
            subscriptions_data = await calendar_queries.get_subscriptions_for_calendar(
                self.client,
                calendar_id
            )
            return subscriptions_data
        except Exception as e:
            raise DatabaseError("get_calendar_subscriptions_service", str(e))

    async def delete_subscription(
        self,
        subscription_id: UUID,
        subscriber_to_delete: Dict[str, Any] 
    ) -> bool:
        try:
            if subscriber_to_delete.get("role") == SubscriptionRole.owner.value:
                raise DatabaseError("owner_delete_prevented", "Pemilik (Owner) kalender tidak dapat dihapus.")
            
            success = await calendar_queries.delete_subscription_by_id(
                self.client,
                subscription_id
            )
            
            if success:
                # --- Panggilan ini SUDAH BENAR menggunakan 'await' ---
                await log_action(
                    user_id=self.user.id,
                    action="calendar.subscription_delete",
                    details={
                        "subscription_id": str(subscription_id),
                        "deleted_user_id": str(subscriber_to_delete.get("user_id")),
                        "calendar_id": str(subscriber_to_delete.get("calendar_id"))
                    }
                )
            
            return success
        except Exception as e:
            if isinstance(e, (DatabaseError, NotFoundError)): raise
            raise DatabaseError("delete_subscription_service", str(e))