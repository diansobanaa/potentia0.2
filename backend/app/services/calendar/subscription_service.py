# File: backend/app/services/calendar/subscription_service.py
# (File Diperbarui dengan Audit Logging)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING, Optional

# Impor Model
from app.models.user import User
from app.models.schedule import SubscriptionRole, SubscriptionCreate
# Impor Kueri
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
# --- [PENAMBAHAN BARU] ---
from app.services.audit_service import log_action
# --- [AKHIR PENAMBAHAN] ---

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

class SubscriptionService:
    """
    Service untuk menangani logika bisnis terkait
    berbagi Kalender (Subscriptions).
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client = auth_info["client"]
        logger.debug(f"SubscriptionService diinisialisasi untuk User: {self.user.id}")

    async def create_new_subscription(
        self, 
        calendar_id: UUID,
        payload: SubscriptionCreate
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk menambahkan pengguna baru ke kalender.
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} menambahkan user {payload.user_id} ke kalender {calendar_id}...")
        
        # Fallback: Cek apakah pengguna sudah di-subscribe
        existing_sub = await calendar_queries.get_user_subscription(
            self.client, payload.user_id, calendar_id
        )
        
        if existing_sub:
            # TODO: Implementasi 'update_subscription_role'
            raise DatabaseError("invite_conflict", "Pengguna sudah berlangganan ke kalender ini.")

        try:
            # Panggil kueri 'create_subscription'
            new_subscription = await calendar_queries.create_subscription(
                self.client,
                payload.user_id,
                calendar_id,
                payload.role
            )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            log_action(
                user_id=self.user.id,
                action="calendar.subscription_create",
                details={
                    "subscription_id": str(new_subscription['subscription_id']),
                    "calendar_id": str(calendar_id),
                    "target_user_id": str(payload.user_id),
                    "role_granted": payload.role.value
                }
            )
            # --- [AKHIR PENAMBAHAN] ---
            
            return new_subscription

        except Exception as e:
            logger.error(f"Error di SubscriptionService.create_new_subscription: {e}", exc_info=True)
            if "invite_conflict" in str(e) or "unique_user_calendar_subscription" in str(e):
                 raise DatabaseError("invite_conflict", "Pengguna sudah berlangganan ke kalender ini.")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError("create_subscription_service", str(e))

    async def get_calendar_subscriptions(self, calendar_id: UUID) -> List[Dict[str, Any]]:
        """
        Logika bisnis untuk mengambil daftar subscriber (hanya-baca).
        """
        logger.info(f"User {self.user.id} mengambil daftar subscriber untuk kalender {calendar_id}...")
        try:
            subscriptions_data = await calendar_queries.get_subscriptions_for_calendar(
                self.client,
                calendar_id
            )
            return subscriptions_data
            
        except Exception as e:
            logger.error(f"Error di SubscriptionService.get_calendar_subscriptions: {e}", exc_info=True)
            raise DatabaseError("get_calendar_subscriptions_service", str(e))

    async def delete_subscription(
        self,
        subscription_id: UUID,
        # Kita tambahkan data 'subscriber' dari dependency keamanan
        subscriber_to_delete: Dict[str, Any] 
    ) -> bool:
        """
        Logika bisnis untuk menghapus/mengeluarkan anggota dari kalender.
        (Sekarang dengan Audit Logging dan Fallback 'owner').
        """
        logger.info(f"User {self.user.id} menghapus subscription {subscription_id}...")
        
        try:
            # Fallback: Mencegah penghapusan 'owner'
            if subscriber_to_delete.get("role") == SubscriptionRole.owner.value:
                # TODO: Cek apakah ada owner lain sebelum mengizinkan penghapusan
                logger.warning(f"Upaya untuk menghapus 'owner' subscription ({subscription_id}) diblokir.")
                raise DatabaseError("owner_delete_prevented", "Pemilik (Owner) kalender tidak dapat dihapus.")
            
            success = await calendar_queries.delete_subscription_by_id(
                self.client,
                subscription_id
            )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            if success:
                log_action(
                    user_id=self.user.id,
                    action="calendar.subscription_delete",
                    details={
                        "subscription_id": str(subscription_id),
                        "deleted_user_id": str(subscriber_to_delete.get("user_id")),
                        "calendar_id": str(subscriber_to_delete.get("calendar_id"))
                    }
                )
            # --- [AKHIR PENAMBAHAN] ---
            
            return success
            
        except Exception as e:
            logger.error(f"Error di SubscriptionService.delete_subscription: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("delete_subscription_service", str(e))