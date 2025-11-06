from pydantic import BaseModel, Field
from typing import Literal

"""
Mendefinisikan Pydantic model untuk setiap objek JSON
yang dikirim melalui ndjson (Newline Delimited JSON) stream.
"""

class StreamTitleChunk(BaseModel):
    """
    Potongan (chunk) dari stream judul (Endpoint B).
    Bisa ada banyak pesan ini.
    """
    type: Literal["title_chunk"] = Field("title_chunk", description="Tipe pesan: potongan stream judul.")
    content: str = Field(..., description="Potongan teks (kata demi kata) dari judul.")

class StreamError(BaseModel):
    """
    Dikirim jika terjadi error fatal selama stream.
    """
    type: Literal["error"] = Field("error", description="Tipe pesan: terjadi error.")
    detail: str = Field(..., description="Detail pesan error.")
    status_code: int = Field(500, description="Kode status HTTP yang disarankan.")