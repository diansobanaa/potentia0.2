from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any 
from uuid import UUID 

class IEmbeddingService(ABC):
    """
    Interface untuk layanan yang menghasilkan embedding vektor dari teks.
    """
    @abstractmethod
    async def generate_embedding(
        self, 
        text: str, 
        task_type: str = "retrieval_query" # DIUBAH: Tambah parameter
    ) -> List[float]:
        """
        Mengubah string teks menjadi embedding vektor.
        
        :param text: Teks input.
        :param task_type: 'retrieval_query' (untuk RAG) atau 
                          'retrieval_document' (untuk seeding/penyimpanan).
        :return: Daftar float yang merepresentasikan embedding.
        """
        pass

class ILlmService(ABC):
    """Interface untuk layanan generatif LLM dasar (non-tool-calling)."""
    
    @abstractmethod
    async def generate_response(self, prompt: str, temperature: float = 0.1) -> str:
        """
        (DIUBAH) Mengganti nama dari get_response menjadi generate_response.
        Menghasilkan respons teks sederhana dari prompt.
        """
        pass