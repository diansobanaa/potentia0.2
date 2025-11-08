# File: backend/app/db/queries/calendar/calendar_queries.py
# (PERBAIKAN FINAL - Menghapus .single() dari UPDATE/DELETE)

import logging
import re
import asyncio
from uuid import UUID
from typing import Optional, Dict, Any, List, Tuple 
from supabase.client import AsyncClient
from postgrest import APIResponse, APIError
from datetime import datetime 
import pytz 

from app.core.exceptions import DatabaseError, NotFoundError
from app.models.schedule import (
    Calendar, CalendarCreate, SubscriptionRole, Schedule,
    GuestCreate, GuestRole, RsvpStatus 
)
logger = logging.getLogger(__name__)

# --- FUNGSI GET (Tidak Berubah, .single() & .maybe_single() valid di sini) ---
async def get_calendar_by_id(authed_client: AsyncClient, calendar_id: UUID) -> Optional[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("calendars").select("*").eq("calendar_id", str(calendar_id)).maybe_single().execute()
        return response.data if response and response.data else None
    except Exception as e: return None
async def get_user_subscription(authed_client: AsyncClient, user_id: UUID, calendar_id: UUID) -> Optional[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("calendar_subscriptions").select("*").eq("user_id", str(user_id)).eq("calendar_id", str(calendar_id)).maybe_single().execute()
        return response.data if response and response.data else None
    except Exception as e: return None
async def get_calendar_subscribers(authed_client: AsyncClient, calendar_id: UUID) -> List[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("calendar_subscriptions").select("user_id, role").eq("calendar_id", str(calendar_id)).execute()
        return response.data if response.data else []
    except Exception as e: return []
async def get_schedules_needing_expansion(authed_client: AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("schedules").select("*").not_.is_("rrule", "null").eq("is_deleted", False).limit(limit).execute()
        return response.data if response.data else []
    except Exception as e: return []
async def get_instances_for_users_in_range(authed_client: AsyncClient, user_ids: List[UUID], start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    try:
        user_id_strings = [str(uid) for uid in user_ids]
        response: APIResponse = await authed_client.table("schedule_instances").select("user_id, start_time, end_time").in_("user_id", user_id_strings).lt("start_time", end_time.isoformat()).gt("end_time", start_time.isoformat()).eq("is_deleted", False).execute()
        return response.data if response.data else []
    except Exception as e: return []
async def get_subscribed_calendars(authed_client: AsyncClient, user_id: UUID) -> List[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("calendar_subscriptions").select("role, calendar:calendars(*)").eq("user_id", str(user_id)).execute()
        return response.data if response.data else []
    except Exception as e: return []
async def get_schedule_by_id(authed_client: AsyncClient, schedule_id: UUID) -> Optional[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("schedules").select("*").eq("schedule_id", str(schedule_id)).eq("is_deleted", False).maybe_single().execute()
        return response.data if response and response.data else None
    except Exception as e: return None
async def get_subscriptions_for_calendar(authed_client: AsyncClient, calendar_id: UUID) -> List[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("calendar_subscriptions").select("subscription_id, role, user:user_id(user_id, name, email)").eq("calendar_id", str(calendar_id)).execute()
        return response.data if response.data else []
    except Exception as e: return []
async def get_subscription_by_id(authed_client: AsyncClient, subscription_id: UUID) -> Optional[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("calendar_subscriptions").select("*").eq("subscription_id", str(subscription_id)).maybe_single().execute()
        return response.data if response and response.data else None
    except Exception as e: return None
async def get_guests_for_schedule(authed_client: AsyncClient, schedule_id: UUID) -> List[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("schedule_guests").select("*, user:user_id(user_id, name, email)").eq("schedule_id", str(schedule_id)).execute()
        return response.data if response.data else []
    except Exception as e: return []
async def get_guest_by_id(authed_client: AsyncClient, guest_id: UUID) -> Optional[Dict[str, Any]]:
    try:
        response: APIResponse = await authed_client.table("schedule_guests").select("*").eq("guest_id", str(guest_id)).maybe_single().execute()
        return response.data if response and response.data else None
    except Exception as e: return None
async def get_schedule_instances_for_user(authed_client: AsyncClient, user_id: UUID, start_time: datetime, end_time: datetime, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    try:
        user_id_str = str(user_id)
        # --- PERBAIKAN: Hitung total dari kueri pertama ---
        list_response = await authed_client.table("schedule_instances") \
            .select("*", count="exact") \
            .eq("user_id", user_id_str) \
            .lt("start_time", end_time.isoformat()) \
            .gt("end_time", start_time.isoformat()) \
            .eq("is_deleted", False) \
            .order("start_time", desc=False) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        data = list_response.data or []
        total = list_response.count or 0
        # --------------------------------------------------
        return data, total
    except Exception as e:
        logger.error(f"Error get_schedule_instances_for_user (async): {e}", exc_info=True)
        return [], 0


# =======================================================================
# === FUNGSI DENGAN PERBAIKAN INSERT / UPDATE / DELETE ===
# =======================================================================

async def bulk_delete_instances_for_schedule(authed_client: AsyncClient, schedule_id: UUID) -> bool:
    try:
        # .delete() tidak menggunakan .single()
        await authed_client.table("schedule_instances").delete().eq("schedule_id", str(schedule_id)).execute()
        return True
    except Exception as e: return False
async def bulk_insert_instances(authed_client: AsyncClient, instances_batch: List[Dict[str, Any]]) -> bool:
    try:
        if not instances_batch: return True
        # .insert() tidak menggunakan .single()
        await authed_client.table("schedule_instances").insert(instances_batch, returning="minimal").execute()
        return True
    except Exception as e: return False

async def create_calendar(authed_client: AsyncClient, calendar_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # .insert() tidak menggunakan .single()
        response: APIResponse = await authed_client.table("calendars").insert(calendar_data, returning="representation").execute()
        if not response.data: raise DatabaseError("create_calendar", "Gagal membuat kalender.")
        return response.data[0]
    except Exception as e: raise DatabaseError("create_calendar_async", str(e))
async def create_subscription(authed_client: AsyncClient, user_id: UUID, calendar_id: UUID, role: SubscriptionRole) -> Dict[str, Any]:
    payload = {"user_id": str(user_id), "calendar_id": str(calendar_id), "role": role.value}
    try:
        # .insert() tidak menggunakan .single()
        response: APIResponse = await authed_client.table("calendar_subscriptions").insert(payload, returning="representation").execute()
        if not response.data: raise DatabaseError("create_subscription", "Gagal membuat langganan.")
        return response.data[0]
    except Exception as e: raise DatabaseError("create_subscription_async", str(e))

async def update_calendar(
    authed_client: AsyncClient,
    calendar_id: UUID,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await authed_client.table("calendars") \
            .update(update_data, returning="representation") \
            .eq("calendar_id", str(calendar_id)) \
            .execute()
        # ---------------------------------
        
        if not response.data:
            raise NotFoundError("Kalender tidak ditemukan saat update.")
        return response.data[0] # Ambil item pertama dari list
        
    except Exception as e:
        logger.error(f"Error update_calendar (async): {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)): raise
        raise DatabaseError("update_calendar_async", str(e))

async def delete_calendar(authed_client: AsyncClient, calendar_id: UUID) -> bool:
    try:
        # .delete() tidak menggunakan .single()
        await authed_client.table("calendars").delete().eq("calendar_id", str(calendar_id)).execute()
        return True
    except Exception as e: raise DatabaseError("delete_calendar_async", str(e))
    

async def create_schedule(authed_client, data: dict) -> dict:
    """
    Insert 1 baris ke tabel schedules.
    Kalau PostgREST mengeluh kolom tidak ada (PGRST204) otomatis
    membuang kolom tersebut lalu retry sekali.
    """
    try:
        resp = (
            await authed_client.table("schedules")
            .insert(data, returning="representation")
            .execute()
        )
        return resp.data[0]

    except APIError as exc:
        # 1. Kolom tidak ada -> buang & retry
        if exc.code == "PGRST204":
            missing_col = re.search(r"the '(\w+)' column", exc.message)
            if missing_col:
                bad_col = missing_col.group(1)
                logger.warning(
                    "Kolom '%s' tidak ada di tabel schedules, "
                    "menghapus & retry sekali", bad_col
                )
                data.pop(bad_col, None)          # buang
                return await create_schedule(authed_client, data)  # retry

        # 2. Error lain -> raise ulang
        raise DatabaseError("create_schedule", f"{exc.code}: {exc.message}") from exc
    
async def update_schedule(
    authed_client: AsyncClient,
    schedule_id: UUID,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        update_data["updated_at"] = datetime.now(pytz.UTC).isoformat()
        
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await authed_client.table("schedules") \
            .update(update_data, returning="representation") \
            .eq("schedule_id", str(schedule_id)) \
            .execute()
        # ---------------------------------
        
        if not response.data:
            raise NotFoundError("Acara tidak ditemukan saat update.")
        return response.data[0] # Ambil item pertama dari list
        
    except Exception as e:
        logger.error(f"Error update_schedule (async): {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)): raise
        raise DatabaseError("update_schedule_async", str(e))

async def soft_delete_schedule(authed_client: AsyncClient, schedule_id: UUID) -> Dict[str, Any]:
    update_data = {"is_deleted": True, "deleted_at": datetime.now(pytz.UTC).isoformat()}
    try:
        return await update_schedule(authed_client, schedule_id, update_data)
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)): raise
        raise DatabaseError("soft_delete_schedule_async", str(e))
    
async def delete_subscription_by_id(authed_client: AsyncClient, subscription_id: UUID) -> bool:
    try:
        # .delete() tidak menggunakan .single()
        response: APIResponse = await authed_client.table("calendar_subscriptions").delete(returning="representation").eq("subscription_id", str(subscription_id)).execute()
        success = bool(response.data and len(response.data) > 0)
        if not success: raise NotFoundError("Langganan (subscription) tidak ditemukan.")
        return True
    except Exception as e:
        if isinstance(e, NotFoundError): raise
        raise DatabaseError("delete_subscription_async", str(e))
    
async def add_guest_to_schedule(authed_client: AsyncClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # .insert() tidak menggunakan .single()
        response: APIResponse = await authed_client.table("schedule_guests").insert(payload, returning="representation").execute()
        if not response.data: raise DatabaseError("add_guest_to_schedule", "Gagal menambah tamu.")
        return response.data[0]
    except APIError as e:
        if "unique_guest_user_per_schedule" in e.message or \
           "unique_guest_email_per_schedule" in e.message:
            raise DatabaseError("invite_conflict", "Tamu ini sudah diundang.")
        raise DatabaseError("add_guest_api", e.message)
    except Exception as e: raise DatabaseError("add_guest_async", str(e))

async def update_guest_response(
    authed_client: AsyncClient,
    schedule_id: UUID,
    user_id: UUID,
    new_status: RsvpStatus
) -> Dict[str, Any]:
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await authed_client.table("schedule_guests") \
            .update({"response_status": new_status.value}, returning="representation") \
            .eq("schedule_id", str(schedule_id)) \
            .eq("user_id", str(user_id)) \
            .execute()
        # ---------------------------------
        
        if not response.data:
            raise NotFoundError("Tamu tidak ditemukan di acara ini.")
        return response.data[0] # Ambil item pertama dari list
        
    except Exception as e:
        logger.error(f"Error update_guest_response (async): {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)): raise
        raise DatabaseError("update_guest_async", str(e))

async def remove_guest_from_schedule(authed_client: AsyncClient, guest_id: UUID) -> bool:
    try:
        # .delete() tidak menggunakan .single()
        response: APIResponse = await authed_client.table("schedule_guests").delete(returning="representation").eq("guest_id", str(guest_id)).execute()
        success = bool(response.data and len(response.data) > 0)
        if not success: raise NotFoundError("Tamu (guest) tidak ditemukan.")
        return True
    except Exception as e:
        if isinstance(e, NotFoundError): raise
        raise DatabaseError("remove_guest_async", str(e))