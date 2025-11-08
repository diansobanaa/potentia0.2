# File: backend/app/db/queries/calendar/calendar_queries.py
# (File Diperbarui)

import logging
import asyncio
from uuid import UUID
from typing import Optional, Dict, Any, List, Tuple 
from supabase import Client
from postgrest import APIResponse, APIError
from datetime import datetime 

# Impor dari aplikasi
from app.core.exceptions import DatabaseError, NotFoundError

from app.models.schedule import (
    Calendar, CalendarCreate, SubscriptionRole, Schedule,
    GuestCreate, GuestRole, RsvpStatus 
)
# Mendefinisikan logger untuk file ini
logger = logging.getLogger(__name__)


async def get_calendar_by_id(
    authed_client: Client, 
    calendar_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Mengambil data satu kalender berdasarkan ID-nya.
    (Digunakan oleh dependency keamanan).
    """
    
    def sync_db_call() -> Optional[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("calendars") \
                .select("*") \
                .eq("calendar_id", str(calendar_id)) \
                .maybe_single() \
                .execute()
            
            if response is None:
                logger.warning(f"Supabase client mengembalikan None untuk get_calendar_by_id {calendar_id}")
                return None
            
            return response.data if response.data else None
            
        except APIError as e:
            logger.error(f"APIError get_calendar_by_id: {e.message}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error get_calendar_by_id: {e}", exc_info=True)
            return None
            
    try:
        calendar_data = await asyncio.to_thread(sync_db_call)
        return calendar_data
    except Exception as e:
        logger.error(f"Error di get_calendar_by_id (async): {e}", exc_info=True)
        return None


async def get_user_subscription(
    authed_client: Client,
    user_id: UUID,
    calendar_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Memeriksa langganan (subscription) spesifik
    seorang pengguna ke kalender tertentu.
    (Digunakan oleh dependency keamanan).
    """
    
    def sync_db_call() -> Optional[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("calendar_subscriptions") \
                .select("*") \
                .eq("user_id", str(user_id)) \
                .eq("calendar_id", str(calendar_id)) \
                .maybe_single() \
                .execute()
                
            if response is None:
                logger.warning(f"Supabase client mengembalikan None untuk get_user_subscription (U:{user_id}, C:{calendar_id})")
                return None
            
            return response.data if response.data else None

        except APIError as e:
            logger.error(f"APIError get_user_subscription: {e.message}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error get_user_subscription: {e}", exc_info=True)
            return None
            
    try:
        subscription_data = await asyncio.to_thread(sync_db_call)
        return subscription_data
    except Exception as e:
        logger.error(f"Error di get_user_subscription (async): {e}", exc_info=True)
        raise DatabaseError("get_user_subscription_async", str(e))

# =======================================================================
# === FUNGSI BARU UNTUK BACKGROUND JOB (TODO-SVC-2) ===
# =======================================================================

async def get_calendar_subscribers(
    authed_client: Client,
    calendar_id: UUID
) -> List[Dict[str, Any]]:
    """
    (BARU) Mengambil daftar 'user_id' yang berlangganan
    ke sebuah kalender. Diperlukan oleh background job ekspansi
    untuk denormalisasi 'user_id' ke 'ScheduleInstances'.
    """
    
    def sync_db_call() -> List[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("calendar_subscriptions") \
                .select("user_id, role") \
                .eq("calendar_id", str(calendar_id)) \
                .execute()
            
            return response.data if response.data else []

        except APIError as e:
            logger.error(f"APIError get_calendar_subscribers: {e.message}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error get_calendar_subscribers: {e}", exc_info=True)
            return []
            
    try:
        subscribers = await asyncio.to_thread(sync_db_call)
        return subscribers
    except Exception as e:
        logger.error(f"Error di get_calendar_subscribers (async): {e}", exc_info=True)
        return []

async def get_schedules_needing_expansion(
    authed_client: Client,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    (BARU) Mengambil 'Schedules' yang berulang (RRULE)
    dan yang baru saja dimodifikasi (version > processed_version).
    
    (Catatan: Kita perlu menambahkan kolom 'processed_version' ke 'Schedules'
    atau menggunakan 'updated_at' untuk melacak ini. 
    Untuk saat ini, kita ambil semua yang memiliki RRULE).
    """
    
    def sync_db_call() -> List[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # TODO: Tambahkan logika filter 'version' atau 'updated_at'
            #       untuk membuatnya lebih efisien daripada mengambil *semua*.
            response: APIResponse = authed_client.table("schedules") \
                .select("*") \
                .not_.is_("rrule", "null") \
                .eq("is_deleted", False) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []

        except APIError as e:
            logger.error(f"APIError get_schedules_needing_expansion: {e.message}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error get_schedules_needing_expansion: {e}", exc_info=True)
            return []
            
    try:
        schedules = await asyncio.to_thread(sync_db_call)
        return schedules
    except Exception as e:
        logger.error(f"Error di get_schedules_needing_expansion (async): {e}", exc_info=True)
        return []

async def bulk_delete_instances_for_schedule(
    authed_client: Client,
    schedule_id: UUID
) -> bool:
    """
    (BARU) Menghapus semua 'ScheduleInstances' yang ada
    untuk 'schedule_id' tertentu sebelum penyisipan batch baru.
    """
    
    def sync_db_call() -> bool:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedule_instances") \
                .delete() \
                .eq("schedule_id", str(schedule_id)) \
                .execute()
            
            # Berhasil bahkan jika tidak ada yang dihapus (data=kosong)
            return True

        except APIError as e:
            logger.error(f"APIError bulk_delete_instances_for_schedule: {e.message}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error bulk_delete_instances_for_schedule: {e}", exc_info=True)
            return False
            
    try:
        success = await asyncio.to_thread(sync_db_call)
        return success
    except Exception as e:
        logger.error(f"Error di bulk_delete_instances_for_schedule (async): {e}", exc_info=True)
        return False

async def bulk_insert_instances(
    authed_client: Client,
    instances_batch: List[Dict[str, Any]]
) -> bool:
    """
    (BARU) Menyisipkan batch besar dari 'ScheduleInstances'
    yang sudah dihitung (pre-computed).
    """
    
    def sync_db_call() -> bool:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            if not instances_batch:
                return True # Tidak ada yang dilakukan
                
            response: APIResponse = authed_client.table("schedule_instances") \
                .insert(instances_batch) \
                .execute()
            
            return bool(response.data)

        except APIError as e:
            logger.error(f"APIError bulk_insert_instances: {e.message}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error bulk_insert_instances: {e}", exc_info=True)
            return False
            
    try:
        success = await asyncio.to_thread(sync_db_call)
        return success
    except Exception as e:
        logger.error(f"Error di bulk_insert_instances (async): {e}", exc_info=True)
        return False
    
    # =======================================================================
# === FUNGSI BARU UNTUK FREE/BUSY SERVICE (TODO-SVC-3) ===
# =======================================================================

async def get_instances_for_users_in_range(
    authed_client: Client,
    user_ids: List[UUID],
    start_time: datetime,
    end_time: datetime
) -> List[Dict[str, Any]]:
    """
    (BARU) Mengambil 'ScheduleInstances' yang tumpang tindih
    dengan rentang waktu yang diminta untuk daftar pengguna.
    Ini adalah fallback SQL untuk 'FreeBusyService'.
    """
    
    def sync_db_call() -> List[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Konversi list UUID ke list string
            user_id_strings = [str(uid) for uid in user_ids]
            
            # Logika Kueri Overlap:
            # Acara (A) tumpang tindih dengan Rentang (R) jika:
            # (A.start < R.end) AND (A.end > R.start)
            response: APIResponse = authed_client.table("schedule_instances") \
                .select("user_id, start_time, end_time") \
                .in_("user_id", user_id_strings) \
                .lt("start_time", end_time.isoformat()) \
                .gt("end_time", start_time.isoformat()) \
                .eq("is_deleted", False) \
                .execute()
            
            return response.data if response.data else []

        except APIError as e:
            logger.error(f"APIError get_instances_for_users_in_range: {e.message}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error get_instances_for_users_in_range: {e}", exc_info=True)
            return []
            
    try:
        instances = await asyncio.to_thread(sync_db_call)
        return instances
    except Exception as e:
        logger.error(f"Error di get_instances_for_users_in_range (async): {e}", exc_info=True)
        return []
    

    # =======================================================================
# === FUNGSI BARU UNTUK ENDPOINT CRUD (TODO-API-2) ===
# =======================================================================

async def create_calendar(
    authed_client: Client,
    calendar_data: Dict[str, Any] # Payload dari CalendarCreate
) -> Dict[str, Any]:
    """
    (BARU) Membuat satu entri 'Calendar' baru di database.
    """
    def sync_db_call() -> Dict[str, Any]:
        try:
            response: APIResponse = authed_client.table("calendars") \
                .insert(calendar_data) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise DatabaseError("create_calendar", "Gagal membuat kalender, tidak ada data dikembalikan.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError create_calendar: {e.message}", exc_info=True)
            raise DatabaseError("create_calendar_api", e.message)
        except Exception as e:
            logger.error(f"Error create_calendar (sync): {e}", exc_info=True)
            raise DatabaseError("create_calendar_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e # Lempar ulang error (DatabaseError)


async def create_subscription(
    authed_client: Client,
    user_id: UUID,
    calendar_id: UUID,
    role: SubscriptionRole
) -> Dict[str, Any]:
    """
    (BARU) Membuat satu entri 'CalendarSubscription' baru.
    (Digunakan saat membuat kalender baru untuk 'owner').
    """
    payload = {
        "user_id": str(user_id),
        "calendar_id": str(calendar_id),
        "role": role.value
    }
    def sync_db_call() -> Dict[str, Any]:
        try:
            response: APIResponse = authed_client.table("calendar_subscriptions") \
                .insert(payload) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise DatabaseError("create_subscription", "Gagal membuat langganan, tidak ada data dikembalikan.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError create_subscription: {e.message}", exc_info=True)
            raise DatabaseError("create_subscription_api", e.message)
        except Exception as e:
            logger.error(f"Error create_subscription (sync): {e}", exc_info=True)
            raise DatabaseError("create_subscription_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e


async def get_subscribed_calendars(
    authed_client: Client,
    user_id: UUID
) -> List[Dict[str, Any]]:
    """
    (BARU) Mengambil daftar kalender yang di-subscribe oleh pengguna.
    (Untuk endpoint GET /api/v1/calendars).
    """
    def sync_db_call() -> List[Dict[str, Any]]:
        try:
            # Kita JOIN ke tabel 'calendars' untuk mendapatkan detailnya
            response: APIResponse = authed_client.table("calendar_subscriptions") \
                .select("role, calendar:calendars(*)") \
                .eq("user_id", str(user_id)) \
                .execute()
            
            return response.data if response.data else []
            
        except APIError as e:
            logger.error(f"APIError get_subscribed_calendars: {e.message}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error get_subscribed_calendars (sync): {e}", exc_info=True)
            return []
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di get_subscribed_calendars (async): {e}", exc_info=True)
        return []

async def update_calendar(
    authed_client: Client,
    calendar_id: UUID,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    (BARU) Memperbarui data 'Calendar' (misal: nama, warna).
    (Untuk endpoint PATCH /api/v1/calendars/{id}).
    """
    def sync_db_call() -> Dict[str, Any]:
        try:
            response: APIResponse = authed_client.table("calendars") \
                .update(update_data) \
                .eq("calendar_id", str(calendar_id)) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise NotFoundError("Kalender tidak ditemukan saat update.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError update_calendar: {e.message}", exc_info=True)
            raise DatabaseError("update_calendar_api", e.message)
        except Exception as e:
            logger.error(f"Error update_calendar (sync): {e}", exc_info=True)
            raise DatabaseError("update_calendar_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e

async def delete_calendar(
    authed_client: Client,
    calendar_id: UUID
) -> bool:
    """
    (BARU) Menghapus 'Calendar'.
    (Untuk endpoint DELETE /api/v1/calendars/{id}).
    'ON DELETE CASCADE' di database akan menangani subscriptions, schedules, dll.
    """
    def sync_db_call() -> bool:
        try:
            response: APIResponse = authed_client.table("calendars") \
                .delete() \
                .eq("calendar_id", str(calendar_id)) \
                .execute()
            
            # Delete tidak selalu mengembalikan data, anggap sukses jika tidak ada error
            return True
            
        except APIError as e:
            logger.error(f"APIError delete_calendar: {e.message}", exc_info=True)
            raise DatabaseError("delete_calendar_api", e.message)
        except Exception as e:
            logger.error(f"Error delete_calendar (sync): {e}", exc_info=True)
            raise DatabaseError("delete_calendar_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e
    
    # =======================================================================
# === FUNGSI BARU UNTUK RESOURCE SCHEDULES (TODO-API-3) ===
# =======================================================================

async def create_schedule(
    authed_client: Client,
    schedule_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    (BARU) Membuat satu entri 'Schedule' (sumber kebenaran) baru.
    Ini adalah langkah pertama sebelum background job melakukan ekspansi.
    """
    def sync_db_call() -> Dict[str, Any]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedules") \
                .insert(schedule_data) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise DatabaseError("create_schedule", "Gagal membuat acara, tidak ada data dikembalikan.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError create_schedule: {e.message}", exc_info=True)
            raise DatabaseError("create_schedule_api", e.message)
        except Exception as e:
            logger.error(f"Error create_schedule (sync): {e}", exc_info=True)
            raise DatabaseError("create_schedule_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e # Lempar ulang error (DatabaseError)


async def get_schedule_by_id(
    authed_client: Client,
    schedule_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    (BARU) Mengambil data "sumber kebenaran" (source of truth)
    dari satu acara berdasarkan ID-nya.
    """
    def sync_db_call() -> Optional[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedules") \
                .select("*") \
                .eq("schedule_id", str(schedule_id)) \
                .eq("is_deleted", False) \
                .maybe_single() \
                .execute()
            
            if response is None:
                logger.warning(f"Supabase client mengembalikan None untuk get_schedule_by_id {schedule_id}")
                return None
            return response.data if response.data else None
            
        except APIError as e:
            logger.error(f"APIError get_schedule_by_id: {e.message}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error get_schedule_by_id (sync): {e}", exc_info=True)
            return None
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di get_schedule_by_id (async): {e}", exc_info=True)
        return None


async def update_schedule(
    authed_client: Client,
    schedule_id: UUID,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    (BARU) Memperbarui data "sumber kebenaran" (source of truth) acara.
    (Misal: mengubah RRULE, menambah EXDATE, atau mengubah judul).
    """
    def sync_db_call() -> Dict[str, Any]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Tambahkan 'version' dan 'updated_at' secara otomatis
            update_data["updated_at"] = datetime.now(pytz.UTC).isoformat()
            
            response: APIResponse = authed_client.table("schedules") \
                .update(update_data) \
                .eq("schedule_id", str(schedule_id)) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise NotFoundError("Acara tidak ditemukan saat update.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError update_schedule: {e.message}", exc_info=True)
            raise DatabaseError("update_schedule_api", e.message)
        except Exception as e:
            logger.error(f"Error update_schedule (sync): {e}", exc_info=True)
            raise DatabaseError("update_schedule_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e


async def soft_delete_schedule(
    authed_client: Client,
    schedule_id: UUID
) -> Dict[str, Any]:
    """
    (BARU) Melakukan soft delete pada 'Schedule' (sumber kebenaran).
    Ini akan memicu background job untuk menghapus 'instances'.
    """
    update_data = {
        "is_deleted": True,
        "deleted_at": datetime.now(pytz.UTC).isoformat()
    }
    
    # Kita panggil ulang fungsi update yang sudah ada
    try:
        return await update_schedule(authed_client, schedule_id, update_data)
    except Exception as e:
        logger.error(f"Error selama soft_delete_schedule: {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise
        raise DatabaseError("soft_delete_schedule_async", str(e))
    

# =======================================================================
# === FUNGSI BARU UNTUK RESOURCE SUBSCRIPTIONS (TODO-API-4) ===
# =======================================================================

async def get_subscriptions_for_calendar(
    authed_client: Client,
    calendar_id: UUID
) -> List[Dict[str, Any]]:
    """
    (BARU) Mengambil daftar subscriber untuk satu kalender.
    (Untuk endpoint GET /api/v1/calendars/{id}/subscriptions).
    """
    def sync_db_call() -> List[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Kita JOIN ke tabel 'Users' untuk mendapatkan detailnya
            response: APIResponse = authed_client.table("calendar_subscriptions") \
                .select("subscription_id, role, user:users(user_id, name, email)") \
                .eq("calendar_id", str(calendar_id)) \
                .execute()
            
            return response.data if response.data else []
            
        except APIError as e:
            logger.error(f"APIError get_subscriptions_for_calendar: {e.message}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error get_subscriptions_for_calendar (sync): {e}", exc_info=True)
            return []
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di get_subscriptions_for_calendar (async): {e}", exc_info=True)
        return []

async def delete_subscription_by_id(
    authed_client: Client,
    subscription_id: UUID
) -> bool:
    """
    (BARU) Menghapus satu entri 'CalendarSubscription' berdasarkan ID-nya.
    (Untuk endpoint DELETE /api/v1/subscriptions/{id}).
    """
    def sync_db_call() -> bool:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("calendar_subscriptions") \
                .delete(returning="representation") \
                .eq("subscription_id", str(subscription_id)) \
                .execute()
            
            # Jika data ada, berarti penghapusan berhasil
            return bool(response.data and len(response.data) > 0)
            
        except APIError as e:
            logger.error(f"APIError delete_subscription_by_id: {e.message}", exc_info=True)
            raise DatabaseError("delete_subscription_api", e.message)
        except Exception as e:
            logger.error(f"Error delete_subscription_by_id (sync): {e}", exc_info=True)
            raise DatabaseError("delete_subscription_sync", str(e))
            
    try:
        success = await asyncio.to_thread(sync_db_call)
        if not success:
            raise NotFoundError("Langganan (subscription) tidak ditemukan.")
        return True
    except Exception as e:
        raise e # Lempar ulang error (DatabaseError/NotFoundError)
    
# =======================================================================
# === FUNGSI BARU UNTUK RESOURCE GUESTS (TODO-API-5) ===
# =======================================================================

async def add_guest_to_schedule(
    authed_client: Client,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    (BARU) Menambahkan satu tamu (via email atau user_id)
    ke tabel 'schedule_guests'.
    """
    def sync_db_call() -> Dict[str, Any]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedule_guests") \
                .insert(payload) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise DatabaseError("add_guest_to_schedule", "Gagal menambah tamu, tidak ada data dikembalikan.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError add_guest_to_schedule: {e.message}", exc_info=True)
            # Tangani fallback unique constraint
            if "unique_guest_user_per_schedule" in e.message or \
               "unique_guest_email_per_schedule" in e.message:
                raise DatabaseError("invite_conflict", "Tamu ini sudah diundang ke acara tersebut.")
            raise DatabaseError("add_guest_api", e.message)
        except Exception as e:
            logger.error(f"Error add_guest_to_schedule (sync): {e}", exc_info=True)
            raise DatabaseError("add_guest_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e # Lempar ulang error (DatabaseError)


async def get_guests_for_schedule(
    authed_client: Client,
    schedule_id: UUID
) -> List[Dict[str, Any]]:
    """
    (BARU) Mengambil daftar tamu untuk satu acara (schedule_id).
    (Untuk endpoint GET /api/v1/schedules/{id}/guests).
    """
    def sync_db_call() -> List[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Kita JOIN ke tabel 'Users' untuk mendapatkan detail (jika ada)
            response: APIResponse = authed_client.table("schedule_guests") \
                .select("*, user:users(user_id, name, email)") \
                .eq("schedule_id", str(schedule_id)) \
                .execute()
            
            return response.data if response.data else []
            
        except APIError as e:
            logger.error(f"APIError get_guests_for_schedule: {e.message}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error get_guests_for_schedule (sync): {e}", exc_info=True)
            return []
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di get_guests_for_schedule (async): {e}", exc_info=True)
        return []


async def get_guest_by_id(
    authed_client: Client,
    guest_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    (BARU) Mengambil satu data tamu berdasarkan 'guest_id'.
    (Digunakan untuk dependency keamanan).
    """
    def sync_db_call() -> Optional[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedule_guests") \
                .select("*") \
                .eq("guest_id", str(guest_id)) \
                .maybe_single() \
                .execute()
            
            return response.data if response.data else None
            
        except APIError as e:
            logger.error(f"APIError get_guest_by_id: {e.message}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error get_guest_by_id (sync): {e}", exc_info=True)
            return None
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di get_guest_by_id (async): {e}", exc_info=True)
        return None


async def update_guest_response(
    authed_client: Client,
    schedule_id: UUID,
    user_id: UUID,
    new_status: RsvpStatus
) -> Dict[str, Any]:
    """
    (BARU) Memperbarui 'response_status' tamu.
    (Untuk endpoint PATCH /.../respond).
    """
    def sync_db_call() -> Dict[str, Any]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedule_guests") \
                .update({"response_status": new_status.value}) \
                .eq("schedule_id", str(schedule_id)) \
                .eq("user_id", str(user_id)) \
                .select("*") \
                .single() \
                .execute()
            
            if not response.data:
                raise NotFoundError("Tamu tidak ditemukan di acara ini.")
            return response.data
            
        except APIError as e:
            logger.error(f"APIError update_guest_response: {e.message}", exc_info=True)
            raise DatabaseError("update_guest_api", e.message)
        except Exception as e:
            logger.error(f"Error update_guest_response (sync): {e}", exc_info=True)
            raise DatabaseError("update_guest_sync", str(e))
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        raise e


async def remove_guest_from_schedule(
    authed_client: Client,
    guest_id: UUID
) -> bool:
    """
    (BARU) Menghapus satu tamu dari 'schedule_guests'
    berdasarkan 'guest_id'-nya.
    """
    def sync_db_call() -> bool:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("schedule_guests") \
                .delete(returning="representation") \
                .eq("guest_id", str(guest_id)) \
                .execute()
            
            return bool(response.data and len(response.data) > 0)
            
        except APIError as e:
            logger.error(f"APIError remove_guest_from_schedule: {e.message}", exc_info=True)
            raise DatabaseError("remove_guest_api", e.message)
        except Exception as e:
            logger.error(f"Error remove_guest_from_schedule (sync): {e}", exc_info=True)
            raise DatabaseError("remove_guest_sync", str(e))
            
    try:
        success = await asyncio.to_thread(sync_db_call)
        if not success:
            raise NotFoundError("Tamu (guest) tidak ditemukan.")
        return True
    except Exception as e:
        raise e
    

# =======================================================================
# === FUNGSI BARU UNTUK RESOURCE VIEWS (TODO-API-6) ===
# =======================================================================

async def get_schedule_instances_for_user(
    authed_client: Client,
    user_id: UUID,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    offset: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (BARU) Mengambil 'ScheduleInstances' yang sudah dihitung (pre-computed)
    untuk satu pengguna dalam rentang waktu, dengan paginasi.
    
    Ini adalah kueri utama untuk endpoint 'GET /view/schedules'.
    """
    
    def sync_db_call() -> Tuple[List[Dict[str, Any]], int]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Konversi UUID ke string
            user_id_str = str(user_id)
            
            # Logika Kueri Overlap:
            # (A.start < R.end) AND (A.end > R.start)
            
            # 1. Ambil data yang dipaginasi
            list_response: APIResponse = authed_client.table("schedule_instances") \
                .select("*") \
                .eq("user_id", user_id_str) \
                .lt("start_time", end_time.isoformat()) \
                .gt("end_time", start_time.isoformat()) \
                .eq("is_deleted", False) \
                .order("start_time", desc=False) \
                .range(offset, offset + limit - 1) \
                .execute()

            # 2. Hitung total
            # (Kita harus mengulang filter untuk hitungan yang akurat)
            count_response: APIResponse = authed_client.table("schedule_instances") \
                .select("instance_id", count="exact") \
                .eq("user_id", user_id_str) \
                .lt("start_time", end_time.isoformat()) \
                .gt("end_time", start_time.isoformat()) \
                .eq("is_deleted", False) \
                .execute()
            
            data = list_response.data or []
            total = count_response.count or 0
            return data, total
            
        except APIError as e:
            logger.error(f"APIError get_schedule_instances_for_user: {e.message}", exc_info=True)
            return [], 0
        except Exception as e:
            logger.error(f"Error get_schedule_instances_for_user (sync): {e}", exc_info=True)
            return [], 0
            
    try:
        return await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di get_schedule_instances_for_user (async): {e}", exc_info=True)
        return [], 0