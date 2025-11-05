import hashlib
import json
from typing import Any

def calculate_checksum(data: Any) -> str:
    """Menghitung MD5 checksum dari data (string atau dict)."""
    if isinstance(data, dict):
        # Pastikan urutan kunci konsisten untuk dict
        encoded_data = json.dumps(data, sort_keys=True).encode('utf-8')
    elif isinstance(data, str):
        encoded_data = data.encode('utf-8')
    else:
        # Tangani tipe lain jika perlu, atau raise error
        encoded_data = str(data).encode('utf-8') 
        
    return hashlib.md5(encoded_data).hexdigest()
