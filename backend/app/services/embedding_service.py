import google.generativeai as genai
from typing import List
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

async def generate_embedding(text: str) -> List[float]:
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []