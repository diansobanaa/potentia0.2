# 🗺️ Status Proyek & Visi Potentia

File ini adalah dokumen instruksi UNTUK AI MODEL. 
Yang melacak visi, status, dan peta jalan (roadmap) untuk proyek Potentia. Ini berfungsi sebagai "sumber kebenaran" (source of truth) untuk kolaborasi pengembangan kita.

---

## 🧭 Blueprint Strategi: Mewujudkan Potensi

### Bagian 1: "Why" Kami (Alasan Eksistensi & Manifesto)
"Mewujudkan Potensi" (To Realize Potential)

Kami percaya bahwa potensi terbaik umat manusia—visi terbesar, ide paling cemerlang, dan impian paling berani—seringkali mati dalam keheningan, terjebak oleh inersia dan alat-alat pasif yang hanya bisa menunggu. Status quo dari software adalah sebagai 'gudang data' yang diam, yang telah gagal secara fundamental untuk menjembatani jurang antara niat dan kenyataan.

Karena itulah kami ada: **Untuk mewujudkan potensi.**

Kami ada untuk menjadi kekuatan proaktif pertama yang menolak untuk menunggu. Kami adalah percikan api yang menyalakan aksi, mitra yang memastikan setiap niat hebat memiliki kesempatan untuk menjadi pencapaian yang hebat.

### Bagian 2: Siapa Kami (Peran & Identitas)
Kita adalah **Mitra Proaktif (The Proactive Partner)**. Kita bukan sekadar alat yang menunggu; kita adalah asisten yang memulai, katalisator yang mendorong, dan eksekutor yang memastikan visi terwujud. Kita menantang status quo software pasif dengan menjadi kekuatan aktif pertama yang benar-benar berinvestasi dalam kesuksesan pengguna kami.

### Bagian 3: Visi Kami (Dunia dalam 10 Tahun)
Sebuah dunia di mana setiap individu, keluarga, dan organisasi dapat mewujudkan potensi penuh mereka, dibebaskan dari inersia dan kompleksitas oleh mitra AI yang proaktif dan cerdas. Menciptakan mitra proaktif yang mengubah visi menjadi realitas bagi individu, keluarga, tim, dan organisasi di seluruh dunia.

### Bagian 4: Misi Kami (Apa yang Kami Lakukan Setiap Hari)
Menciptakan Agen AI Proaktif yang mengubah visi dan niat menjadi realitas yang terukur bagi individu dan tim yang ambisius di seluruh dunia.

### Bagian 5: Strategi Inti Kami (Cara Kami Menang)
* **Diferensiasi Kunci:** Kami menang dengan menjadi **Asisten Proaktif**, bukan Alat Pasif.
* **Fokus Pasar Awal:** Kami akan mendominasi satu *Beachhead Market* terlebih dahulu untuk membuktikan model kami sebelum berekspansi.

### Bagian 6: Nilai-Nilai Inti Kami (Prinsip Pemandu)
* Proaktif, Bukan Pasif.
* Potensi di Atas Segalanya.
* Manusiawi & Suportif.
* Berani Menantang Status Quo.
* Mengangkat Kehidupan (Elevate Lives).

### Kerangka Inti (Universal)
* **The Visionaries:** Mendorong Transformasi Visioner (Fokus: Aksi agresif, pertumbuhan, eksekusi berani).
* **The Organizers:** Membangun Pondasi Akuntabilitas (Fokus: Sistem pendukung, kejelasan, ketepatan).
* **The Starters:** Memicu Aksi Berkelanjutan (Fokus: Mengatasi inersia, membangun keberanian, menjaga disiplin).

---

## 🎯 Fokus Saat Ini: Backend API

Poin ini sangat penting: Saat ini kita **hanya mengerjakan backend API** untuk proyek `potentia0.2`.

Semua file yang sedang kita kerjakan (Python, FastAPI, Supabase, Pydantic) adalah fondasi sisi server. Kita sedang membangun "mesin" dan "otak" dari aplikasi.

Kita **tidak** sedang mengerjakan sisi klien (UI/Frontend) yang akan menggunakan API ini.

---

## 🤖 Instruksi untuk AI Model (Partner Kolaborasi)

Arahan berikut akan digunakan untuk memandu kolaborasi pengembangan kita:
1.  **Ikuti Gaya Kode:** Selalu ikuti pola dan gaya penulisan kode yang sudah ada di dalam *source code* proyek `potentia0.2`. Jika ada beberapa gaya, tanyakan untuk konfirmasi
2.  **Pemisahan Tanggung Jawab:** Pastikan kita memisahkan file secara ketat (Models, DB/Queries, Services, API/Endpoints).
3.  **Refactor adalah Kunci:** Prioritaskan kode yang bersih, modular, dan mudah dibaca.
4.  **Struktur Folder:** Untuk fitur yang kompleks, buat sub-folder agar tetap teratur (refactor).
5.  **Beri Komentar:** Selalu berikan komentar di setiap fungsi atau logika yang kompleks untuk menjelaskan tujuannya.
6.  **Best Practices:** Ikuti standar industri (seperti yang dilakukan perusahaan besar) untuk keamanan, skalabilitas, dan *maintainability*.
7.  **Tangkap oleh Fallback:** Jika data dari database kosong, tangkap oleh fallback
8.  **Selalu gunakan try exept:** 

---

## 📊 Status Fitur (Sesuai Flowchart "v2 alpha")

Berikut adalah analisis status fitur *backend* berdasarkan *flowchart* "conversation v2 alpha" dan kode yang ada.

### ✅ Fitur yang Sudah Selesai

Sebagian besar dari alur kerja "v2 alpha" telah berhasil diimplementasikan. Arsitektur 3-panggilan (Judge, Specialist, Assessor) sudah berjalan penuh.

1.  **Orkestrasi AI 3-Panggilan (Judge, Specialist, Assessor)**
    * Logika utama di `ChatService` (`handle_chat_turn_full_pipeline`) secara akurat mencerminkan alur *flowchart*.
    * **Panggilan #1 (Judge):** `s1` dan `s2` diimplementasikan dengan memanggil `self.judge_chain.ainvoke`.
    * **Panggilan #2 (Specialist):** `s5` diimplementasikan dengan memanggil `self.specialist_executor`.
    * **Panggilan #3 (Assessor):** `n56` diimplementasikan dengan `self._run_assessor_call`.

2.  **Sistem Konteks (Judge & Memory Manager)**
    * `s1 (n5, n6, n4)`: Fitur "Muat Data Context Aktif" dan "Ambil 50 pesan terakhir" diimplementasikan dengan sempurna oleh `ContextManager`.
    * `s2 (n14, n15, n16)`: Logika `Context Judge` (Continue, Switch, New) diimplementasikan di `ChatService`.
    * `s3 (n22, n25)`: `Memory Manager` diimplementasikan oleh `ContextManager` yang memanggil kueri di `context_queries.py` untuk membuat atau memuat konteks.

3.  **Jalur Tulis Asinkron (Async Write Path)**
    * `s4 (n43, n56)`: Fitur "Input data Setelah tampilkan jawaban" diimplementasikan menggunakan `BackgroundTasks` di `chat.py`.
    * `n56` (Input ke `user_preferences`): Diimplementasikan dengan sempurna oleh `save_preferences_to_db` di `user_preference_memory_service.py`.
    * `n44` (Insert text user & AI): Diimplementasikan oleh `save_turn_messages` di `message_queries.py`.

4.  **Personalisasi Prompt (Bagian dari `s5`)**
    * `n47` (Ambil `user_preferences` & `user_Semantic_memories`): Fitur ini **SELESAI**. `ContextPacker` secara eksplisit memanggil `get_user_facts_and_rules` dan `get_user_semantic_memories` dan memasukkannya ke dalam *prompt*.

### ❌ Fitur yang Belum Selesai (Prioritas Selanjutnya)

Berikut adalah komponen inti dari *flowchart* "v2 alpha" yang menjadi fokus kita selanjutnya.

1.  **Antrian Embedding Pesan (Node `s4: n40, n41, n42`)**
    * **Deskripsi:** *Flowchart* Anda di `s4` memiliki alur kerja untuk memasukkan pesan ke "tabel embedding Queue" (`n40`) untuk mengisi `MessageEmbeddingAssistant` dan `MessageEmbeddingUser` (`n41`).
    * **Status: Belum Selesai.**
    * **Analisis Kode:** Saat ini, `message_queries.save_turn_messages` hanya menyimpan teks mentah. Tidak ada logika untuk membuat *embedding* dari pesan-pesan tersebut. Ini sesuai dengan catatan di `TODO.txt` ("tabel message masuk, tabel embedding belum.").

2.  **RAG Kontekstual (Node `n51: RAG jika ada`)**
    * **Deskripsi:** *Prompt* akhir di `s5` seharusnya menyertakan `n51: RAG jika ada`. Ini adalah RAG untuk data kontekstual:
        1.  **Ingatan Riwayat:** (misal: "ingat angka 1000").
        2.  **Konteks Canvas:** (misal: "analisis blok saya").
    * **Status: Belum Selesai (Diblokir oleh #1).**
    * **Analisis Kode:** `ContextPacker` **belum** memanggil fungsi RAG seperti `find_relevant_history` atau `find_relevant_blocks`. Fitur "Ingatan Riwayat" tidak akan berfungsi sampai fitur #1 (Antrian Embedding Pesan) diimplementasikan.

3.  **Implementasi Domain Prompt (Prompt Peran)**
    * **Deskripsi:** Ini adalah bagian dari RAG Kontekstual (n51). Tujuannya adalah agar AI secara dinamis memilih "Domain Prompt" (misal: "Analis Data", "Editor") menggunakan RPC `find_relevant_role_id` dan memasukkannya ke *prompt* akhir.
    * **Status: Belum Selesai.**
    * **Analisis Kode:** `ContextPacker` saat ini belum memanggil `find_relevant_role_id` dan masih menggunakan `developer_prompt.py` secara statis.