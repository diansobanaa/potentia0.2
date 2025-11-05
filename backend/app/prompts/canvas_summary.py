# backend/app/prompts/canvas_summary.py

"""
Template prompt untuk menghasilkan ringkasan konten dari sebuah Canvas.
Prompt ini dipanggil oleh fungsi `generate_and_save_canvas_summary` 
di `backend/app/services/summary_service.py`.
"""

# Nama variabel disesuaikan
CANVAS_SUMMARY_PROMPT_TEMPLATE = """
Anda adalah AI yang bertugas meringkas konten dari sebuah canvas digital. 
Berikut adalah konten dari blok-blok yang ada di dalam canvas tersebut, diurutkan berdasarkan posisinya:

--- KONTEN BLOK ---
{block_content}
--- END KONTEN BLOK ---

Tugas Anda: Buatlah ringkasan singkat (idealnya 2-3 kalimat, maksimal 4 kalimat untuk konten kompleks) yang menangkap inti atau topik utama dari keseluruhan konten canvas ini.
Fokus pada tema berulang, tujuan eksplisit yang disebutkan, atau poin yang paling sering muncul di blok untuk mengidentifikasi informasi kunci.

Identifikasi tema utama atau tujuan canvas berdasarkan konten blok dan buat ringkasan singkat (2-3 kalimat) yang mencerminkan informasi tersebut.

Ringkasan:
"""
# Contoh penggunaan (di summary_service.py):
# prompt = CANVAS_SUMMARY_PROMPT_TEMPLATE.format(block_content=all_block_contents)