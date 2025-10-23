import google.generativeai as genai
from app.core.config import settings # Pastikan settings diimpor dengan benar
from typing import AsyncIterable # <-- Impor tipe AsyncIterable

# Konfigurasi API key Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# PERUBAHAN: Fungsi ini sekarang mengembalikan AsyncIterable[str]
async def stream_gemini_response(prompt: str) -> AsyncIterable[str]:
    """
    Mengirimkan prompt ke Google Gemini API dan mengembalikan stream respons teks.
    """
    try:
        # Gunakan nama model preview yang valid
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025') 
        
        # PERUBAHAN: Gunakan generate_content_async dengan stream=True
        stream = await model.generate_content_async(prompt, stream=True) 
        
        # PERUBAHAN: Iterasi melalui stream dan yield setiap potongan teks
        async for chunk in stream:
            if chunk.parts:
                yield chunk.text
            else:
                # Tangani kasus di mana chunk tidak memiliki teks (misalnya, akhir stream atau diblokir)
                # Anda bisa log finish_reason atau safety_ratings di sini jika perlu
                finish_reason = chunk.candidates[0].finish_reason if chunk.candidates else "Unknown"
                safety_ratings = chunk.candidates[0].safety_ratings if chunk.candidates else "Unknown"
                print(f"Gemini stream chunk empty. Finish reason: {finish_reason}, Safety: {safety_ratings}")
                # Anda bisa memilih untuk yield string kosong atau tidak sama sekali

    except Exception as e:
        # Tangani error API atau lainnya
        print(f"Error calling Gemini API stream: {e}")
        # Saat streaming, error lebih sulit ditangani. Kita bisa yield pesan error.
        yield f"Maaf, terjadi error saat menghubungi AI: {str(e)}"

# Fungsi lama (non-streaming) bisa Anda hapus atau simpan sebagai alternatif
async def call_gemini_api(prompt: str) -> str:
    """
    (Versi Lama - Non-Streaming)
    Mengirimkan prompt ke Google Gemini API dan mengembalikan respons teks lengkap.
    """
    full_response = ""
    try:
        async for chunk in stream_gemini_response(prompt):
             full_response += chunk
        # Jika stream menghasilkan pesan error, kembalikan itu
        if "Maaf, terjadi error" in full_response:
             return full_response
        # Periksa jika full_response kosong setelah streaming selesai
        if not full_response:
             print("Warning: Gemini stream completed but resulted in an empty response.")
             return "Maaf, AI tidak memberikan respons."
        return full_response
    except Exception as e:
        print(f"Error collecting full response from Gemini stream: {e}")
        return "Maaf, saya sedang mengalami kesulitan teknis untuk merespons."

