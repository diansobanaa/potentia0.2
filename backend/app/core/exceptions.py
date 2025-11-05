# PARSE: 08-custom-exceptions.py
from typing import Any

class DataAccessError(Exception):
    """Base exception untuk error pada repository layer."""
    pass

class PromptNotFoundError(DataAccessError):
    """Error ketika prompt yang 'active' tidak ditemukan."""
    def __init__(self, message: str = "Prompt 'active' tidak ditemukan."):
        self.message = message
        super().__init__(self.message)

class RpcError(DataAccessError):
    """Error ketika memanggil Supabase RPC."""
    def __init__(self, function_name: str, error: Any):
        self.message = f"Gagal memanggil RPC '{function_name}': {error}"
        super().__init__(self.message)

class DatabaseError(DataAccessError):
    """Error umum database (insert/update)."""
    def __init__(self, operation: str, error: Any):
        self.message = f"Operasi database '{operation}' gagal: {error}"
        super().__init__(self.message)

class EmbeddingGenerationError(Exception):
    """Error ketika gagal menghasilkan embedding."""
    def __init__(self, message: str):
        self.message = f"Gagal menghasilkan embedding: {message}"
        super().__init__(self.message)

class DatabaseError(Exception):
    """
    Pengecualian umum untuk kesalahan terkait operasi database.
    (Kita juga menggunakan ini di kode kita)
    """
    pass

class NotFoundError(Exception):
    """
    (BARU - INI YANG MEMPERBAIKI ERROR)
    Dimunculkan ketika sebuah resource (misal: konteks, kanvas, pengguna)
    tidak dapat ditemukan di database.
    """
    pass