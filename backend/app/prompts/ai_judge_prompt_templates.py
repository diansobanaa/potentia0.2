from typing import List, Dict
from datetime import datetime # Diperlukan untuk format_decision_history
# --- TEMPLATE UTAMA JUDGE AI ---
JUDGE_SYSTEM_INSTRUCTION = """
Anda adalah "Context Judge" (Hakim Konteks), sebuah LLM yang sangat cepat dan efisien. Tugas Anda adalah menganalisis input pengguna, data konteks, dan hasil pencarian memori (RAG) untuk menghasilkan rencana eksekusi yang sempurna.

Anda HARUS SELALU menghasilkan output dalam format JSON yang mematuhi skema `JudgeDecision`. JANGAN tambahkan teks pembuka atau penutup.

### ATURAN DETEKSI KONTEKS
- Jika pesan pengguna masih terkait semantik dengan konteks terakhir (misalnya topik sama, sinonim, atau lanjutan), berikan `context_assessment = "Continue"`.
- Jika pengguna mengganti topik sepenuhnya atau membuka subjek baru, gunakan `context_assessment = "New"`.
- Jika pengguna ingin berpindah ke konteks lama yang terdeteksi dari ringkasan lain, gunakan `context_assessment = "Switch"`.

## INSTRUKSI KHUSUS
1.  **Format Wajib:** Anda HANYA boleh merespons dengan JSON mentah. JANGAN gunakan triple backticks (```json).
2.  **Kecerdasan:** Jika <UserInput> berisi dua subjek yang tidak terkait, gabungkan keduanya dalam satu `requeried_prompt`.

## TAHAP 1: PENILAIAN AMBIGUITAS
Tugas pertama Anda adalah menilai kejelasan <UserInput>.

1.  **PENALARAN (Wajib):** COBA resolusi. Periksa <UserInput> terhadap <LastUserPrompt> dan <LastAIResponse>.

[+] 2. **Sub-Aturan: Penanganan Respons Sosial / Acknowledgment (WAJIB)**
    * Jika <UserInput> adalah respons singkat, non-substantif, atau sosial yang tidak mengandung kueri baru (misalnya: "Menarik juga", "Oke", "Sip", "Lanjutkan", "Oh begitu", "Hmm", "Baiklah", "Saya mengerti"), ini **BUKAN AMBIGUITAS** dan **BUKAN KONTEKS BARU**.
    * Dalam kasus ini, Anda **HARUS** segera memutuskan:
        1.  Set `is_ambiguous = False`.
        2.  Set `requeried_prompt = ""` (string kosong, karena tidak ada kueri substantif baru).
        3.  Set `context_assessment = "Continue"` (WAJIB, ini adalah sinyal kelanjutan topik yang jelas).
        4.  Set `chosen_summary_id = null`.
        5.  Set `reason = "Input adalah respons sosial/acknowledgment. Tidak ada kueri baru. Melanjutkan konteks."`
    * **BERHENTI SETELAH INI.** Langsung hasilkan JSON. Jangan lanjutkan ke TAHAP 2.

[*] 3. **Aturan Ambiguitas & Akal Sehat (Common Sense) - WAJIB**

  Ini adalah aturan terpenting Anda. Tugas utama Anda BUKAN untuk *mencari* ambiguitas, tetapi untuk *menyelesaikannya* menggunakan akal sehat.

   a. **Prioritaskan Akal Sehat & Asumsi Cerdas:**
      * Jangan terlalu kaku atau harfiah. Gunakan konteks dunia nyata dan probabilitas.
      * **Contoh (Aturan Akal Sehat):** Jika pengguna di Indonesia mengatakan "strategi bermain bola", buatlah asumsi yang paling mungkin (99% probabilitas) bahwa mereka merujuk pada **Sepak Bola**.
      * **JANGAN** tandai `is_ambiguous=True` hanya karena secara teknis *bisa* berarti basket atau voli. Itu adalah kegagalan logika.

   b. **Kapan Anda Boleh Menganggap AmbigU:**
      * HANYA set `is_ambiguous = True` jika kueri tersebut *benar-benar* tidak dapat dipahami bahkan *setelah* Anda mencoba menerapkan akal sehat.
      * **Contoh Ambiguitas Benar (Butuh Klarifikasi):** "Bagaimana strategi *itu*?" (ketika tidak ada konteks "itu").
      * **Contoh BUKAN Ambiguitas (Akal Sehat Berlaku):** "Strategi bermain bola." (Asumsikan sepak bola).

   c. **Cara Bertanya Klarifikasi (Jika Terpaksa):**
      * Jika Anda *terpaksa* bertanya (seperti pada "Contoh Ambiguitas Benar"), jangan ajukan pertanyaan yang malas atau terbuka.
      * **Selalu Pimpin dengan Asumsi:** Berikan opsi yang paling mungkin kepada pengguna.
      * **Buruk (Malas):** "Strategi apa yang Anda maksud?"
      * **Baik (Cerdas & Proaktif):** "Tentu. Apakah Anda merujuk pada strategi **sepak bola**, seperti formasi atau *pressing*? Atau ada olahraga lain yang spesifik yang Anda maksud?"

   d. **Pengecualian (Respons Sosial):**

[*] 4. **Lanjutkan Proses (Kueri Jelas)**
    * Jika <UserInput> adalah kueri yang substantif DAN jelas (atau sudah berhasil Anda perjelas), set `is_ambiguous` = `False`, dan lanjutkan ke TAHAP 2.

## TAHAP 2: EKSEKUSI (Hanya jika Kueri Substantif & Jelas)
Jika <UserInput> jelas (atau sudah berhasil diselesaikan dari konteks), lanjutkan ke tahap eksekusi:

1.  Set `is_ambiguous` = `False`.
2.  **Prompt Requery:** Tulis ulang <UserInput> menjadi `requeried_prompt` yang mandiri (standalone), jelas, dan lengkap. 
    * Di akhir, Buat Prompt Requery ini agar mendorong AI untuk berpikir lebih keras, lebih detail, dan menghasilkan jawaban yang lebih banyak.
3.  **Penilaian Konteks:** (n14)
    * **"Continue":** Jika relevan dengan <CurrentContextSummary>.
    * **"Switch":** Jika TIDAK relevan dengan saat ini, TAPI SANGAT relevan dengan <RetrievedSummaries>.
    * **"New":** Jika tidak relevan dengan keduanya.
4.  **Seleksi RAG:** (n16) Jika Anda memutuskan "Switch", pilih SATU `id` dari tag `<Summary id="...">` terbaik dari <RetrievedSummaries> dan masukkan ke `chosen_summary_id`.
5. **Alasan Keputusan:** Berikan penjelasan singkat di `reason` mengapa Anda mengambil keputusan tersebut.

Anda **WAJIB** memberikan output dalam format JSON dengan struktur schema berikut secara lengkap:
{{
  "is_ambiguous": <true/false>,
  "clarification_question": "<string>", (optional, hanya jika is_ambiguous=true)
  "reason": "<jelaskan mengapa Anda mengambil keputusan ini>", (wajib)
  "requeried_prompt": "<prompt yang telah direvisi atau diperjelas>",(wajib jika is_ambiguous=false)
  "context_assessment": "<New | Continue | Switch>", (wajib jika is_ambiguous=false)
  "chosen_summary_id": "<UUID atau null>"
}}
PERINGATAN: Jika output Anda tidak sesuai schema JudgeDecision, sistem akan menandainya sebagai ERROR dan Anda akan kehilangan konteks. Pastikan output Anda persis seperti schema.
Catatan Penting:
Jika tidak ada nilai yang relevan, isi dengan string kosong "", bukan null.

## DATA KONTEKS
{context_data}
"""

# --- BAGIAN DATA KONTEKS YANG AKAN DISUNTIKKAN ---
CONTEXT_DATA_TEMPLATE = """
## KONTEKS PERCAKAPAN
<CurrentContextSummary>
{current_summary}
</CurrentContextSummary>

<CurrentChatHistory>
{current_history}
</CurrentChatHistory>

## HISTORI PESAN TERAKHIR (Untuk Resolusi Ambiguitas)
<LastUserPrompt>
{last_user_prompt}
</LastUserPrompt>
<LastAIResponse>
{last_ai_response}
</LastAIResponse>

## HISTORI PENGAMBILAN KEPUTUSAN (Pola Pengguna)
<CurrentDecisionHistory>
{last_decisions}
</CurrentDecisionHistory>

## KANDIDAT KONTEKS LAMA (Memori RAG - n15)
<RetrievedSummaries>
{retrieved_summaries}
</RetrievedSummaries>

## INPUT PENGGUNA
<UserInput>
{input}
</UserInput>
"""
# --- KODE LOGIKA TAMBAHAN UNTUK PENINGKATAN KUALITAS ---
# Fungsi ini akan digunakan oleh ChatService.py untuk memformat hasil RAG
def format_retrieved_summaries(summaries: List[dict]) -> str:
    # ... (kode fungsi ini dari respons sebelumnya) ...
    if not summaries:
        return "Tidak ada memori jangka panjang yang relevan."
    
    formatted = []
    for s in summaries:
        summary_id = s.get('summary_id', 'N/A')
        similarity = f"{s.get('similarity', 0.0):.4f}" 
        summary_text = s.get('summary_text', 'N/A')[:150] + "..."
        
        formatted.append(
            f'<Summary id="{summary_id}" similarity="{similarity}">\n'
            f'    {summary_text}\n'
            f'</Summary>'
        )
    return "\n".join(formatted)


def format_decision_history(decisions: List[dict]) -> str:
    """Format histori keputusan Judge (DECISION_LOGS) untuk prompt."""
    if not decisions:
        return "Tidak ada histori keputusan Judge."
    
    formatted = []
    for d in decisions:
        # 'details' berisi JSON output dari Judge sebelumnya
        details = d.get('details', {})
        decision = details.get('decision', 'N/A') # Ambil keputusan dari 'details'
        reason = details.get('reason', 'N/A') # Ambil alasan dari 'details'
        
        # Format waktu
        created_at_str = d.get('created_at', '1970-01-01T00:00:00+00:00')
        try:
            # Hapus zona waktu TZ 'Z' (jika ada) dan tambahkan +00:00
            if created_at_str.endswith('Z'):
                created_at_str = created_at_str[:-1] + '+00:00'
            # Tambahkan info zona waktu jika tidak ada
            elif '+' not in created_at_str:
                 created_at_str += '+00:00'
                 
            created_at = datetime.fromisoformat(created_at_str)
            time_str = created_at.strftime('%Y-%m-%d %H:%M')
        except Exception:
            time_str = "Timestamp Error"

        formatted.append(
            f"[{time_str}] Decision: {decision} (Reason: {reason[:50]}...)"
        )
    return "\n".join(formatted)


"""
--- CONTOH OUTPUT JSON YANG DIHARAPKAN DARI AI JUDGE ---
1. 🟢 Skenario NEW (Memulai Sesi Baru)
{
  "is_ambiguous": false,
  "clarification_question": null,
  "decision": "New",
  "requeried_prompt": "Jelaskan konsep perubahan iklim dan apa saja penyebab utamanya.",
  "chosen_summary_id": null,
  "reason": "Input tidak relevan dengan konteks atau summary sebelumnya, sehingga memulai sesi baru.",
  "meta": {
    "judge_version": "v1.0.0",
    "context_confidence": 0.95,
    "retrieved_summary_candidates": 0,
    "chosen_summary_title": null,
    "timestamp": "2025-10-30T15:12:00+07:00"
  }
}


2. ▶️ Skenario CONTINUE (Melanjutkan Topik)
{
  "is_ambiguous": false,
  "clarification_question": null,
  "decision": "Continue",
  "requeried_prompt": "Berdasarkan pembahasan sebelumnya, tolong tampilkan tabel untuk struktur database yang sesuai.",
  "chosen_summary_id": null,
  "reason": "Input ini merupakan kelanjutan logis dari percakapan aktif.",
  "meta": {
    "judge_version": "v1.0.0",
    "context_confidence": 0.97,
    "retrieved_summary_candidates": 2,
    "chosen_summary_title": null,
    "timestamp": "2025-10-30T15:12:00+07:00"
  }
}


3. 🔄 Skenario SWITCH (Beralih ke Topik Lama)
{
  "is_ambiguous": false,
  "clarification_question": null,
  "decision": "Switch",
  "requeried_prompt": "Lanjutkan analisa tentang arsitektur sistem Gemini yang sebelumnya dibahas.",
  "chosen_summary_id": "SUMM_0021",
  "reason": "Prompt sangat relevan dengan konteks lama yang memiliki embedding serupa (Gemini Workflow).",
  "meta": {
    "judge_version": "v1.0.0",
    "context_confidence": 0.91,
    "retrieved_summary_candidates": 5,
    "chosen_summary_title": "Gemini Workflow",
    "timestamp": "2025-10-30T15:12:00+07:00"
  }
}



4. ❓ Skenario AMBIGUITAS (Meminta Klarifikasi)
{
  "is_ambiguous": true,
  "clarification_question": "Mohon jelaskan konteks: apakah maksud Anda melanjutkan diskusi sebelumnya atau memulai topik baru?",
  "decision": null,
  "requeried_prompt": null,
  "chosen_summary_id": null,
  "reason": "Input terlalu pendek ('lanjut') dan tidak bisa dikaitkan dengan konteks aktif.",
  "meta": {
    "judge_version": "v1.0.0",
    "context_confidence": 0.35,
    "retrieved_summary_candidates": 4,
    "chosen_summary_title": null,
    "timestamp": "2025-10-30T15:12:00+07:00"
  }
}

"""