from app.services.redis_rate_limiter import rate_limiter
from typing import Union
from uuid import UUID

# Fungsi-fungsi ini memanggil implementasi Redis

# Tambahkan 'authed_client' sebagai argumen pertama (meskipun mungkin belum dipakai)
def check_guest_limit(authed_client, ip_address: str) -> bool:
    """Memeriksa apakah alamat IP tamu telah mencapai batas pesan."""
    # Meneruskan argumen ke implementasi Redis
    return rate_limiter.check_guest_limit(ip_address)

# Tambahkan 'authed_client' sebagai argumen pertama
def check_user_limit(authed_client, user_id: UUID, tier: str) -> bool:
    """Memeriksa apakah pengguna yang terotentikasi telah mencapai batas pesan."""
    # Meneruskan argumen ke implementasi Redis
    return rate_limiter.check_user_limit(user_id, tier)
