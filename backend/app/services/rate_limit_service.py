from app.services.redis_rate_limiter import rate_limiter
from typing import Union
from uuid import UUID

# Fungsi-fungsi ini sekarang memanggil implementasi Redis
def check_guest_limit(ip_address: str) -> bool:
    return rate_limiter.check_guest_limit(ip_address)

def check_user_limit(user_id: UUID, tier: str) -> bool:
    return rate_limiter.check_user_limit(user_id, tier)