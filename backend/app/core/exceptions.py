# File: backend/app/core/exceptions.py
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

class DatabaseError(Exception):
    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        super().__init__(f"Database error during {operation}: {details}")

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
    def __init__(self, entity: str, entity_id: str):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with ID {entity_id} not found.")

class PermissionError(Exception):
    """
    Dilempar ketika pengguna mencoba melakukan aksi
    yang tidak diizinkan.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)