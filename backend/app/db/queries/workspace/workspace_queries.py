# File: backend/app/db/queries/workspace/workspace_queries.py

import logging  # Diperlukan untuk pencatatan (logging) error dan debug
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import secrets  # Digunakan untuk membuat token undangan yang aman
from supabase import Client
from postgrest import APIResponse
from postgrest.exceptions import APIError  # Untuk penanganan error spesifik Supabase
from app.models.user import User

# Impor model Pydantic untuk validasi tipe data (Enum)
from app.models.workspace import MemberRole, InvitationType
# Impor exceptions kustom untuk error handling yang bersih
from app.core.exceptions import DatabaseError, NotFoundError

# Mendefinisikan logger untuk file ini
logger = logging.getLogger(__name__)


# ====================================================
#  FUNGSI CRUD WORKSPACE (Induk)
# ====================================================

async def create_workspace(authed_client: Client, name: str, workspace_type: str, owner_id: UUID) -> Dict[str, Any]:
    """
    Membuat Workspace baru di tabel 'Workspaces'.
    Fungsi ini dipanggil oleh endpoint POST /workspaces/.
    """
    def sync_call():
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response = authed_client.table("Workspaces").insert({
                "name": name,
                "type": workspace_type,
                "owner_user_id": str(owner_id)
            }, returning="representation").execute()

            # Fallback: jika insert tidak mengembalikan data
            if not response or not getattr(response, "data", None):
                logger.error("Gagal membuat workspace — tidak ada response data.")
                raise DatabaseError("create_workspace", "Response kosong dari Supabase.")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error create_workspace: {e}", exc_info=True)
            raise DatabaseError("create_workspace", str(e))
    # Menjalankan fungsi sinkron di thread terpisah agar tidak memblokir
    return await asyncio.to_thread(sync_call)


async def get_workspace_by_id(authed_client: Client, workspace_id: UUID) -> Optional[dict]:
    """
    Mengambil detail workspace berdasarkan ID.
    Fungsi ini sangat penting untuk 'dependency' keamanan
    guna memeriksa 'owner' dan data workspace.
    """
    def sync_call():
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("Workspaces") \
                .select("*") \
                .eq("workspace_id", str(workspace_id)) \
                .maybe_single() \
                .execute()
            
            # Fallback: Tangguh terhadap response None (misal: 406 Not Acceptable)
            if response is None:
                logger.warning(f"Supabase client mengembalikan None untuk get_workspace_by_id {workspace_id}")
                return None
            
            # Jika 'response.data' kosong, kembalikan None (Not Found)
            return response.data if response.data else None
            
        except APIError as e:
            # Fallback: Menangani error spesifik PostgREST
            logger.error(f"APIError get_workspace_by_id: {e.message}", exc_info=True)
            return None
        except Exception as e:
            # Fallback: Menangani error Python umum
            logger.error(f"Error get_workspace_by_id: {e}", exc_info=True)
            return None
    # Menjalankan fungsi sinkron di thread terpisah
    return await asyncio.to_thread(sync_call)

async def update_workspace(
    authed_client: Client, workspace_id: UUID, user_id: UUID, new_name: str
) -> Dict[str, Any]:
    """
    Memperbarui nama workspace.
    Dipanggil oleh PATCH /workspaces/{id}.
    """
    def sync_call():
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response = authed_client.table("Workspaces") \
                .update({"name": new_name}, returning="representation") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("owner_user_id", str(user_id)) \
                .execute()

            data = getattr(response, "data", None)
            
            # Fallback: Jika tidak ada data (bukan owner atau tidak ada workspace)
            if not data:
                logger.warning(f"Gagal update workspace {workspace_id}, user {user_id} bukan pemilik.")
                raise NotFoundError("Workspace tidak ditemukan atau bukan pemilik.")
            return data[0]
        except NotFoundError:
            raise # Lempar ulang NotFoundError agar endpoint bisa menangani (404)
        except Exception as e:
            logger.error(f"Error update_workspace: {e}", exc_info=True)
            raise DatabaseError("update_workspace", str(e))
    # Menjalankan fungsi sinkron di thread terpisah
    return await asyncio.to_thread(sync_call)


async def delete_workspace(
    authed_client: Client, workspace_id: UUID, user_id: UUID
) -> bool:
    """
    Menghapus workspace.
    Dipanggil oleh DELETE /workspaces/{id}.
    """
    def sync_call():
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response = authed_client.table("Workspaces") \
                .delete(returning="representation") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("owner_user_id", str(user_id)) \
                .execute()

            data = getattr(response, "data", None)
            
            # Fallback: Jika tidak ada data (bukan owner atau tidak ada workspace)
            if not data:
                logger.warning(f"Gagal hapus workspace {workspace_id} — tidak ditemukan atau bukan pemilik.")
                return False
            return True
        except Exception as e:
            # Fallback: Tangkap error jika (misal) FK constraint gagal
            logger.error(f"Error delete_workspace: {e}", exc_info=True)
            return False
    # Menjalankan fungsi sinkron di thread terpisah
    return await asyncio.to_thread(sync_call)


# ====================================================
#  FUNGSI PAGINASI WORKSPACE (List)
# ====================================================

async def get_user_workspaces_paginated(
    authed_client: Client, user_id: UUID, offset: int, limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Mengambil daftar workspace (yang user-nya adalah anggota) dengan paginasi.
    Dipanggil oleh GET /workspaces/.
    """
    def sync_call() -> Tuple[List[Dict[str, Any]], int]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Kueri 1: Ambil data paginasi
            list_response = authed_client.table("WorkspaceMembers") \
                .select("Workspaces(*)") \
                .eq("user_id", str(user_id)) \
                .order("workspace_id", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            # Kueri 2: Ambil total hitungan (count)
            count_response = authed_client.table("WorkspaceMembers") \
                .select("workspace_id", count="exact") \
                .eq("user_id", str(user_id)) \
                .execute()

            # Ekstrak data dengan fallback
            data = getattr(list_response, "data", None) or []
            total = getattr(count_response, "count", 0) or 0
            
            # Urai data join
            workspaces = [item["Workspaces"] for item in data if item.get("Workspaces")]
            return workspaces, total
        except Exception as e:
            logger.error(f"Error paginating user workspaces: {e}", exc_info=True)
            return [], 0 # Kembalikan list kosong saat error
    # Menjalankan fungsi sinkron di thread terpisah
    return await asyncio.to_thread(sync_call)


# ====================================================
#  FUNGSI CRUD ANGGOTA WORKSPACE
# ====================================================

async def check_user_membership(authed_client: Client, workspace_id: UUID, user_id: UUID) -> Optional[dict]:
    """
    Memeriksa apakah pengguna adalah anggota workspace.
    Ini adalah 'Gerbang Keamanan' dasar untuk endpoint.
    """
    def sync_call():
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = authed_client.table("WorkspaceMembers") \
                .select("*") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("user_id", str(user_id)) \
                .maybe_single() \
                .execute()

            # Fallback 1: Jika Supabase client gagal (misal: 406 Not Acceptable)
            if response is None:
                logger.error(f"Supabase client mengembalikan None saat cek keanggotaan (W:{workspace_id}, U:{user_id})")
                return None
                
            # Kasus valid: Pengguna bukan anggota
            if not response.data:
                logger.warning(f"User {user_id} bukan anggota workspace {workspace_id}")
                return None
            
            # Sukses: Pengguna adalah anggota
            return response.data
            
        except APIError as e:
            # Fallback 2: Tangkap error PostgREST
            logger.error(f"APIError check_user_membership (W:{workspace_id}, U:{user_id}): {e.message}", exc_info=True)
            return None
        except Exception as e:
            # Fallback 3: Tangkap error Python/lainnya
            logger.error(f"Error check_user_membership (W:{workspace_id}, U:{user_id}): {e}", exc_info=True)
            return None
            
    return await asyncio.to_thread(sync_call)


async def add_member_to_workspace(
    authed_client: Client, 
    workspace_id: UUID, 
    user_id: UUID, 
    role: MemberRole
) -> Dict[str, Any]:
    """
    Menambahkan (atau memperbarui) pengguna ke workspace (via User ID).
    
    PENTING:
    Fungsi ini HANYA digunakan untuk alur internal 
    seperti 'create_workspace' (dimana Owner ditambahkan secara paksa). 
    Endpoint 'Invite' publik TIDAK memanggil fungsi ini.
    """
    
    payload = {
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "role": role.value
    }

    def sync_call():
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Gunakan 'upsert': jika user sudah ada, update role; jika tidak, insert.
            response = authed_client.table("WorkspaceMembers") \
                .upsert(payload, on_conflict="workspace_id, user_id", returning="representation") \
                .execute()

            if not response or not getattr(response, "data", None):
                logger.error(f"Gagal upsert anggota {user_id} ke workspace {workspace_id}")
                raise DatabaseError("add_member_to_workspace", "Response kosong dari Supabase.")
            
            return response.data[0]
            
        except APIError as e:
            logger.error(f"APIError add_member_to_workspace (sync): {e.message}", exc_info=True)
            # Fallback: jika 'user_id' atau 'workspace_id' tidak ada (FK error)
            if "foreign key constraint" in e.message:
                raise NotFoundError(f"Gagal menambahkan anggota: Workspace atau Pengguna tidak ditemukan.")
            raise DatabaseError("add_member_sync_api", e.message)
        except Exception as e:
            logger.error(f"Error add_member_to_workspace (sync): {e}", exc_info=True)
            raise DatabaseError("add_member_to_workspace", str(e))
            
    return await asyncio.to_thread(sync_call)


async def create_workspace_invitation(
    authed_client: Client,
    workspace_id: UUID,
    inviter_id: UUID,
    role: MemberRole,
    # Menerima salah satu dari ini (sesuai model Pydantic)
    invitee_email: Optional[str] = None,
    invitee_user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Membuat undangan baru di tabel 'WorkspaceInvitations'.
    Ini adalah satu-satunya fungsi yang dipanggil oleh endpoint POST /members,
    sesuai logika "Invite-Only" yang mengharuskan persetujuan.
    """
    
    def sync_db_call() -> Dict[str, Any]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Siapkan payload dasar
            invitation_payload = {
                "workspace_id": str(workspace_id),
                "inviter_user_id": str(inviter_id),
                "role": role.value,
                "status": "pending",
                "token": secrets.token_urlsafe(32), # Token acak yang aman
            }

            # --- Logika Percabangan (Email vs ID) ---
            if invitee_user_id:
                # --- ALUR 1: "INVITE BY ID" ---
                logger.debug(f"Menyiapkan Invite by ID untuk user {invitee_user_id}")
                invitation_payload["invitee_user_id"] = str(invitee_user_id)
                invitation_payload["type"] = InvitationType.USER_ID.value # Mengisi 'type'

                # Fallback 1: Cek apakah pengguna ini sudah menjadi anggota
                member_check = authed_client.table("WorkspaceMembers").select("id").eq("workspace_id", str(workspace_id)).eq("user_id", str(invitee_user_id)).execute()
                if member_check.data:
                    raise DatabaseError("invite_conflict", "Pengguna ini sudah menjadi anggota workspace.")

                # Fallback 2: Cek apakah pengguna ini sudah diundang
                pending_check = authed_client.table("WorkspaceInvitations").select("invitation_id").eq("workspace_id", str(workspace_id)).eq("invitee_user_id", str(invitee_user_id)).eq("status", "pending").execute()
                if pending_check.data:
                    raise DatabaseError("invite_conflict", "Pengguna ini sudah memiliki undangan yang tertunda (pending).")

            elif invitee_email:
                # --- ALUR 2: "INVITE BY EMAIL" ---
                logger.debug(f"Menyiapkan Invite by Email untuk {invitee_email}")
                invitation_payload["invitee_email"] = invitee_email
                invitation_payload["type"] = InvitationType.EMAIL.value # Mengisi 'type'
            
                # Fallback 1: Cek apakah email ini sudah menjadi anggota
                member_check = (
                    authed_client.table("WorkspaceMembers")
                    .select("user:user_id(email)")
                    .eq("workspace_id", str(workspace_id))
                    .execute()
                )
                if member_check.data:
                    for member in member_check.data:
                        if member.get("user") and member["user"].get("email") == invitee_email:
                            raise DatabaseError("invite_conflict", "Pengguna dengan email ini sudah menjadi anggota workspace.")

                # Fallback 2: Cek apakah email ini sudah diundang
                pending_check = (
                    authed_client.table("WorkspaceInvitations")
                    .select("invitation_id")
                    .eq("workspace_id", str(workspace_id))
                    .eq("invitee_email", invitee_email)
                    .eq("status", "pending")
                    .execute()
                )
                if pending_check.data:
                    raise DatabaseError("invite_conflict", "Pengguna dengan email ini sudah memiliki undangan yang tertunda (pending).")
            
            # Fallback: Seharusnya tidak pernah terjadi berkat Pydantic
            else:
                 raise ValueError("Harus menyediakan invitee_email atau invitee_user_id.")

            # --- Akhir Logika Percabangan ---

            # Lanjutkan Insert ke 'WorkspaceInvitations'
            response: APIResponse = (
                authed_client.table("WorkspaceInvitations")
                .insert(invitation_payload, returning="representation")
                .execute()
            )
            
            # Fallback 3: Gagal insert
            if not response.data:
                raise DatabaseError("invite_create_fail", "Gagal membuat undangan di database.")
                
            return response.data[0]
            
        except APIError as e:
            # Menangkap error spesifik dari Supabase
            logger.error(f"APIError create_workspace_invitation (sync): {e.message}", exc_info=True)
            if "invite_conflict" in str(e):
                 raise
            raise DatabaseError("invite_create_sync_api", e.message)
        except Exception as e:
            # Menangkap error Python (termasuk 'invite_conflict' dari DatabaseError)
            logger.error(f"Error create_workspace_invitation (sync): {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError, ValueError)):
                raise # Lempar ulang error yang kita kenali
            raise DatabaseError("invite_create_sync_general", str(e))

    try:
        data = await asyncio.to_thread(sync_db_call)
        return data
    except Exception as e:
        logger.error(f"Error di create_workspace_invitation (async): {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError, ValueError)):
            raise 
        raise DatabaseError("invite_create_async", f"Error tidak terduka: {str(e)}")


async def list_workspace_members(
    authed_client: Client, 
    workspace_id: UUID
) -> List[Dict[str, Any]]:
    """
    Mengambil daftar anggota dari 'WorkspaceMembers'
    DAN menggabungkannya (JOIN) dengan info 'Users' (nama, email).
    Dipanggil oleh GET /.../members.
    """
    
    def sync_db_call() -> List[Dict[str, Any]]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            response: APIResponse = (
                authed_client.table("WorkspaceMembers")
                .select("role, user:user_id(user_id, name, email)")
                .eq("workspace_id", str(workspace_id))
                .execute()
            )
            # Fallback: Kembalikan list kosong jika tidak ada data
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error list_workspace_members (sync) {workspace_id}: {e}", exc_info=True)
            raise DatabaseError("list_workspace_members_sync", str(e))

    try:
        data = await asyncio.to_thread(sync_db_call)
        return data
    except Exception as e:
        logger.error(f"Error di list_workspace_members (async): {e}", exc_info=True)
        raise DatabaseError("list_workspace_members_async", f"Error tidak terduka: {str(e)}")


async def update_workspace_member_role(
    authed_client: Client, 
    workspace_id: UUID, 
    user_id_to_update: UUID, 
    new_role: MemberRole
) -> Dict[str, Any]:
    """
    Memperbarui 'role' dari seorang anggota di 'WorkspaceMembers'.
    Dipanggil oleh PATCH /.../members/{user_id}.
    """
    
    def sync_db_call() -> Dict[str, Any]:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Fallback 1: Dapatkan Owner ID dari workspace
            # Kita gunakan get_workspace_by_id yang sudah tangguh
            workspace = authed_client.table("Workspaces").select("owner_user_id").eq("workspace_id", str(workspace_id)).maybe_single().execute()
            if not workspace or not workspace.data:
                 raise NotFoundError("Workspace tidak ditemukan.")
            
            owner_id = workspace.data.get("owner_user_id")

            # Fallback 2: Cegah Owner di-demote (diturunkan rolenya)
            if str(user_id_to_update) == str(owner_id) and new_role != MemberRole.admin:
                raise DatabaseError("owner_demote_prevented", "Pemilik (Owner) workspace harus selalu menjadi Admin.")

            # Lanjutkan update
            response: APIResponse = (
                authed_client.table("WorkspaceMembers")
                .update({"role": new_role.value}, returning="representation")
                .eq("workspace_id", str(workspace_id))
                .eq("user_id", str(user_id_to_update))
                .execute()
            )
            
            # Fallback 3: Anggota tidak ditemukan
            if not response.data or len(response.data) == 0:
                raise NotFoundError(f"Anggota dengan ID {user_id_to_update} tidak ditemukan di workspace ini.")
            
            return response.data[0]

        except Exception as e:
            # Menangkap semua error, termasuk 'owner_demote_prevented'
            logger.error(f"Error update_workspace_member_role (sync): {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise # Lempar ulang error yang kita kenali
            raise DatabaseError("update_role_sync", str(e))

    try:
        data = await asyncio.to_thread(sync_db_call)
        return data
    except Exception as e:
        logger.error(f"Error di update_workspace_member_role (async): {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("update_role_async", f"Error tidak terduka: {str(e)}")


async def remove_workspace_member(
    authed_client: Client, 
    workspace_id: UUID, 
    user_id_to_remove: UUID
) -> bool:
    """
    Menghapus seorang anggota dari 'WorkspaceMembers'.
    Dipanggil oleh DELETE /.../members/{user_id}.
    """
    
    def sync_db_call() -> bool:
        """Membungkus panggilan database sinkron (blocking)"""
        try:
            # Fallback 1: Dapatkan Owner ID dari workspace
            workspace = authed_client.table("Workspaces").select("owner_user_id").eq("workspace_id", str(workspace_id)).maybe_single().execute()
            if not workspace or not workspace.data:
                 raise NotFoundError("Workspace tidak ditemukan.")
            
            owner_id = workspace.data.get("owner_user_id")

            # Fallback 2: Cegah Owner dihapus
            if str(user_id_to_remove) == str(owner_id):
                raise DatabaseError("owner_remove_prevented", "Pemilik (Owner) workspace tidak dapat dihapus.")

            # Lanjutkan penghapusan
            response: APIResponse = (
                authed_client.table("WorkspaceMembers")
                .delete(returning="representation")
                .eq("workspace_id", str(workspace_id))
                .eq("user_id", str(user_id_to_remove))
                .execute()
            )
            
            # Fallback 3: Anggota tidak ditemukan
            if not response.data or len(response.data) == 0:
                raise NotFoundError(f"Anggota dengan ID {user_id_to_remove} tidak ditemukan di workspace ini.")
            return True
            
        except Exception as e:
            # Menangkap semua error, termasuk 'owner_remove_prevented'
            logger.error(f"Error remove_workspace_member (sync): {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise # Lempar ulang error yang kita kenali
            raise DatabaseError("remove_member_sync", str(e))
    try:
        success = await asyncio.to_thread(sync_db_call)
        return success
    except Exception as e:
        logger.error(f"Error di remove_workspace_member (async): {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("remove_member_async", f"Error tidak terduka: {str(e)}")
    
# ====================================================
#  FUNGSI LOGIKA UNDANGAN (BARU)
# ====================================================

def _find_invitation_by_token(
    authed_client: Client, 
    token: str
) -> Optional[Dict[str, Any]]:
    """
    Helper SINKRON: Mengambil undangan 'pending' berdasarkan token.
    (Hanya untuk dipanggil oleh 'respond_to_workspace_invitation')
    """
    try:
        response: APIResponse = authed_client.table("WorkspaceInvitations") \
            .select("*") \
            .eq("token", token) \
            .eq("status", "pending") \
            .maybe_single() \
            .execute()
            
        if response is None:
            logger.warning(f"Panggilan _find_invitation_by_token mengembalikan None (token: {token[:5]}...)")
            return None
        return response.data if response.data else None
        
    except Exception as e:
        logger.error(f"Error di _find_invitation_by_token: {e}", exc_info=True)
        return None

def _delete_invitation_by_token(
    authed_client: Client, 
    token: str
) -> bool:
    """
    Helper SINKRON: Menghapus undangan setelah diproses (diterima/ditolak).
    (Hanya untuk dipanggil oleh 'respond_to_workspace_invitation')
    """
    try:
        response: APIResponse = authed_client.table("WorkspaceInvitations") \
            .delete() \
            .eq("token", token) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Error di _delete_invitation_by_token: {e}", exc_info=True)
        return False


async def respond_to_workspace_invitation(
    authed_client: Client,
    token: str,
    action: str, # "accept" atau "reject"
    user: User   # Pengguna yang sedang login
) -> Optional[Dict[str, Any]]:
    """
    Orkestrator Logika untuk menerima atau menolak undangan workspace.
    
    Fitur:
    1. Memvalidasi token dan keamanan (memastikan token untuk user yang benar).
    2. Menghapus token (consume) setelah dipakai.
    3. Jika 'accept', memanggil 'add_member_to_workspace' untuk
       menambahkan pengguna ke workspace.
    """
    
    # --- Langkah 1: Validasi Undangan ---
    invitation = await asyncio.to_thread(_find_invitation_by_token, authed_client, token)
    
    # Fallback 1: Token tidak valid atau sudah dipakai
    if not invitation:
        raise NotFoundError("Undangan ini tidak valid atau telah kedaluwarsa.")

    # --- Langkah 2: Validasi Keamanan (Sangat Penting) ---
    # Memastikan pengguna yang login adalah orang yang benar.
    invitee_email = invitation.get("invitee_email")
    invitee_user_id = invitation.get("invitee_user_id")
    
    if invitee_email and invitee_email.lower() != user.email.lower():
        # Kasus: Diundang via email, tapi login dengan akun yang salah
        raise DatabaseError("invite_permission_denied", "Undangan ini ditujukan untuk alamat email yang berbeda.")
    
    if invitee_user_id and str(invitee_user_id) != str(user.id):
        # Kasus: Diundang via ID, tapi login dengan akun yang salah
        raise DatabaseError("invite_permission_denied", "Undangan ini ditujukan untuk pengguna yang berbeda.")

    # --- Langkah 3: Eksekusi Aksi ---
    
    # Ambil detail untuk aksi "accept"
    workspace_id = invitation.get("workspace_id")
    role = invitation.get("role", "guest") # Default ke 'guest' jika role null

    # HAPUS/KONSUMSI token SEKARANG.
    # Kita lakukan ini *sebelum* aksi agar token tidak bisa dipakai dua kali,
    # bahkan jika aksi 'accept' gagal.
    await asyncio.to_thread(_delete_invitation_by_token, authed_client, token)

    if action == "reject":
        logger.info(f"Pengguna {user.id} menolak undangan ke workspace {workspace_id}")
        return {"status": "rejected"}
    
    if action == "accept":
        logger.info(f"Pengguna {user.id} menerima undangan ke workspace {workspace_id} sebagai {role}")
        
        # Panggil fungsi 'add_member_to_workspace' yang sudah ada
        # untuk menambahkan pengguna secara 'upsert'.
        new_member_data = await add_member_to_workspace(
            authed_client=authed_client,
            workspace_id=UUID(workspace_id),
            user_id=user.id,
            role=MemberRole(role) # Konversi string ke Enum
        )
        return new_member_data
        
    return None # Seharusnya tidak pernah sampai sini