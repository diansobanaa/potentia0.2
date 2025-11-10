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

## 📊 Status Fitur (Update per 7 November 2025)

Bagian ini mencatat kemajuan implementasi CRUD API berdasarkan daftar di `TODO.txt`.

### Resource 4: Canvases (✅ Selesai)

Tujuan implementasi CRUD penuh untuk `canvases` telah tercapai. Logika keamanan inti telah diperbarui untuk mendukung arsitektur "Invite-Ready".

* **Keamanan (`CanvasAccessDep`)**: Fondasi keamanan di `app/core/dependencies.py` telah berhasil di-refactor.
    * `get_canvas_access` sekarang memeriksa 3 jalur akses: Pemilik Personal, Anggota Workspace, dan Undangan (Invite) via `CanvasAccess`.
    * Ini memastikan bahwa semua endpoint yang menggunakan *dependency* ini secara otomatis mendukung logika berbagi/invite.
    * `get_canvas_by_id` di `app/db/queries/canvas/canvas_queries.py` telah diperkuat dengan *fallback* `maybe_single()` untuk mencegah *crash* 404.

* **`GET /{canvas_id}` (Detail)**: ✅ Selesai. Dilindungi oleh `CanvasAccessDep`.
* **`PATCH /{canvas_id}/meta` (Update)**: ✅ Selesai.
    * Endpoint `PATCH` generik telah diganti dengan endpoint `PATCH .../meta` yang lebih spesifik.
    * Menggunakan model `CanvasMetaUpdate` dengan `ConfigDict(extra="forbid")` untuk validasi *payload* yang ketat (hanya `title` dan `icon`).
* **`POST /{canvas_id}/archive` (Update)**: ✅ Selesai.
* **`POST /{canvas_id}/restore` (Update)**: ✅ Selesai.
    * Logika *update* status (`is_archived`) dipisah dari *update* metadata untuk desain API yang lebih bersih.
* **`DELETE /{canvas_id}` (Delete)**: ✅ Selesai.
    * Endpoint ini menangani *hard delete*.
    * Memiliki *fallback* tangguh yang mengembalikan `409 Conflict` jika canvas masih memiliki `Blocks` (mencegah data yatim).

### Resource 3.1: Canvas Members (✅ Selesai - Fase 1)

Kita telah berhasil mengimplementasikan fitur inti untuk manajemen anggota canvas, yang melengkapi logika *invite* yang telah kita siapkan.

* **Router Baru**: `app/api/v1/endpoints/canvas_members.py` telah dibuat dan diintegrasikan ke `api.py`.
* **Logika Query (Performa Tinggi)**:
    * Kita mengadopsi **Opsi 1 (Solusi RPC)** untuk performa tinggi.
    * Fungsi SQL `get_canvas_members_detailed` telah dibuat untuk menggabungkan 3 sumber anggota (Owner, Workspace, Invite) di dalam database.
    * `app/db/queries/canvas/canvas_member_queries.py` telah diimplementasikan untuk memanggil RPC tersebut, menggantikan logika Python yang "cerewet".
* **`GET /canvases/{id}/members` (List)**: ✅ Selesai.
    * Dilindungi oleh `CanvasAccessDep` (semua anggota bisa melihat).
    * Secara efisien mengembalikan daftar anggota gabungan berkat RPC.
* **`POST /canvases/{id}/members` (Invite)**: ✅ Selesai (Fase 1: Invite by `user_id`).
    * Dilindungi oleh `CanvasAdminAccessDep` (hanya admin/owner yang bisa mengundang).
    * Menggunakan `add_canvas_member` dengan logika `upsert` untuk menambah/memperbarui *role* anggota.
    * Memiliki *fallback* `404 Not Found` jika `user_id` yang diundang tidak ada.

#### Komentar untuk Selanjutnya (Fitur Tertunda)

* **Invite by Email**: Endpoint `POST .../members` saat ini secara eksplisit mengembalikan `501 Not Implemented` untuk *invite* via `email`. Ini adalah langkah selanjutnya yang logis, yang akan melibatkan penggunaan tabel `CanvasInvitations` dan pengiriman email (seperti yang ada di `notification_service.py`).

Kamu bisa temukan Schema DB di backend\app\db\schema.sql Untuk menentukan strategi fitur

### Resource 3: Workspace Members (✅ Selesai - Fase 1)

Kita telah berhasil mengimplementasikan CRUD penuh untuk manajemen anggota workspace. Logika bisnis inti telah diimplementasikan sesuai arahan: **semua penambahan anggota baru harus melalui alur "Invite-Only"** (memerlukan persetujuan), bukan penambahan langsung (direct add).

* **File Router Baru**: `backend/app/api/v1/endpoints/workspace_members.py` telah dibuat dan diintegrasikan ke `api.py`.
* **File Model Baru**: Skema Pydantic (`WorkspaceMemberInviteOrAdd`, `WorkspaceMemberUpdate`, dll.) telah dibuat di `backend/app/models/workspace.py`.

#### Fitur & Logika yang Diimplementasikan:

1.  **Keamanan (`WorkspaceAdminAccessDep`)**:
    * Sebuah *dependency* keamanan baru (`get_workspace_admin_access`) telah dibuat di `backend/app/core/dependencies.py`.
    * *Dependency* ini secara ketat melindungi endpoint `POST` (Invite), `PATCH` (Update Role), dan `DELETE` (Remove), dan hanya mengizinkan pengguna dengan *role* 'admin'.
    * *Dependency* `get_current_workspace_member` (untuk `GET`) telah diperbaiki untuk menangani *fallback* `None` response dari Supabase dengan aman.

2.  **`POST /` (Invite Member)**: ✅ Selesai.
    * Endpoint ini sekarang menggunakan logika "Invite-Only" yang fleksibel.
    * Admin dapat mengundang anggota baru baik via `user_id` (pengguna internal) maupun `email` (pengguna eksternal).
    * Kedua alur tersebut sekarang memanggil fungsi `create_workspace_invitation`.
    * **Perbaikan Bug**: *Bug* `violates not-null constraint "type"` telah diperbaiki. Fungsi `create_workspace_invitation` sekarang mengisi kolom `type` dengan benar (misal: 'EMAIL' atau 'USER_ID').
    * **Fallback**: Kueri ini memiliki *fallback* tangguh untuk mencegah undangan duplikat (baik untuk `email` maupun `user_id` yang statusnya "pending" atau sudah menjadi anggota).

3.  **`GET /` (List Members)**: ✅ Selesai.
    * Dilindungi oleh `WorkspaceMemberDep` (semua anggota bisa melihat daftar).
    * Menggunakan kueri `list_workspace_members` yang efisien dengan `JOIN` ke tabel `Users` untuk mengambil `name` dan `email`.

4.  **`PATCH /{user_id}` (Update Role)**: ✅ Selesai.
    * Dilindungi oleh `WorkspaceAdminAccessDep`.
    * **Fallback**: Logika kueri `update_workspace_member_role` secara eksplisit **mencegah** seorang admin menurunkan *role* (demote) `owner_user_id` dari workspace.

5.  **`DELETE /{user_id}` (Remove Member)**: ✅ Selesai.
    * Dilindungi oleh `WorkspaceAdminAccessDep`.
    * **Fallback**: Logika kueri `remove_workspace_member` secara eksplisit **mencegah** `owner_user_id` dihapus dari workspaceny-a sendiri.

#### Komentar untuk Selanjutnya (Fitur Tertunda)

* **Endpoint "Accept/Reject"**: Kita telah berhasil membuat alur "kirim undangan" (`POST /.../members`). Langkah berikutnya yang logis adalah membuat endpoint untuk *menerima* undangan tersebut (misal: `POST /invitations/workspace/respond`), yang akan memvalidasi `token` dan memindahkan pengguna dari `WorkspaceInvitations` ke `WorkspaceMembers`.

## 📊 Status Fitur (Update per 9 November 2025)

Kita telah berhasil menyelesaikan implementasi penuh dari **Arsitektur Kalender & Penjadwalan "Calendar-Centric" (v1.2)** serta **Refaktor Asinkron Penuh** pada seluruh *stack* I/O *backend*.

Ini menandai pencapaian teknis besar, memigrasikan aplikasi dari *prototype* berbasis *thread* menjadi arsitektur *non-blocking* yang skalabel.

### 1. Arsitektur Kalender & Jadwal (v1.2 - Selesai)

Fitur inti penjadwalan, yang merupakan fondasi untuk fungsionalitas proaktif, kini telah selesai dan terintegrasi.

* **Skema 5-Tabel:** Seluruh skema database baru telah diimplementasikan: `Calendars`, `CalendarSubscriptions`, `Schedules`, `ScheduleGuests`, dan `ScheduleInstances`.
* **CRUD API Penuh:** Semua *endpoint* yang direncanakan telah dibuat, diimplementasikan, dan di-debug:
    * **Resource `Calendars`:** `POST`, `GET`, `PATCH`, `DELETE` untuk mengelola "folder" kalender.
    * **Resource `Schedules`:** `POST`, `GET`, `PATCH`, `DELETE` untuk mengelola "sumber kebenaran" acara, termasuk validasi `RRULE` di *foreground* untuk mencegah input buruk.
    * **Resource `Subscriptions`:** `POST`, `GET`, `DELETE` untuk manajemen anggota kalender (penambahan langsung).
    * **Resource `Guests`:** `POST`, `GET`, `PATCH /respond` (RSVP), dan `DELETE` untuk manajemen tamu per-acara.
* **Keamanan Granular:** Setiap *endpoint* CUD (Create, Update, Delete) dilindungi oleh *dependency* keamanan granular (`CalendarEditorAccessDep`, `ScheduleAccessDep`, `GuestAccessDep`, `SubscriptionDeleteAccessDep`) untuk memastikan hanya pengguna yang berwenang (misalnya, 'owner' atau 'editor') yang dapat melakukan perubahan.

### 2. Performa & Skalabilitas (Selesai)

Logika *backend* yang krusial untuk performa tinggi kini telah diimplementasikan dan distabilkan.

* **Denormalisasi RRULE (MUST FIX Selesai):** *Background job* di `schedule_expander.py` sekarang secara efisien menghitung dan melakukan denormalisasi (N x M) acara berulang ke tabel `ScheduleInstances` untuk *semua* subscriber. Ini memastikan *query* kalender tetap cepat, tidak peduli berapa banyak acara berulang atau subscriber yang ada.
* **Deteksi Konflik (Free/Busy) Cepat:** `FreeBusyService` telah diimplementasikan dengan strategi "Redis-first". Pengecekan ketersediaan (untuk deteksi konflik) kini menggunakan *cache* Redis ZSET yang *di-cache* dan *non-blocking*, dengan *fallback* ke tabel `ScheduleInstances` yang sudah di-precompute.
* **Tampilan Kalender Cepat:** *Endpoint* utama UI (`GET /view/schedules`) membaca langsung dari tabel `ScheduleInstances` yang terdenormalisasi, memastikan pemuatan kalender yang instan bagi pengguna.

### 3. Refaktor Asinkron Penuh (Selesai)

Seluruh *codebase* *backend* telah berhasil dimigrasi dari arsitektur *sync-over-async* (`asyncio.to_thread`) ke arsitektur **asinkron *native*** penuh.

* **Database (Supabase):** Semua panggilan database di seluruh direktori `app/db/queries/` dan `app/db/repositories/` telah di-refaktor untuk menggunakan `AsyncClient` dengan pemanggilan `await` *native*.
* **Cache (Redis):** *Library* Redis telah dimigrasi ke `redis.asyncio`. Semua operasi *cache* (termasuk *locking* di *jobs* dan *query* di `FreeBusyService`) sekarang sepenuhnya *non-blocking*.
* **Embedding (Google):** Layanan *embedding* telah di-refaktor untuk menggunakan `genai.embed_content_async`, menghilangkan *bottleneck* I/O terakhir.

### 4. Keamanan & Stabilitas (Selesai)

* **Perbaikan Bug Kritis:** Kita telah berhasil men-debug dan memperbaiki serangkaian *error* pasca-refaktor, termasuk `AttributeError` (`.select`, `.single`), `ImportError` (`get_supabase_client`), dan `RuntimeWarning` (`was never awaited`), yang menghasilkan *stack* aplikasi yang stabil.
* **Perbaikan Keamanan IDOR:** Celah keamanan di *endpoint* `DELETE /subscriptions/{id}` telah ditutup dengan mengimplementasikan *dependency* `SubscriptionDeleteAccessDep`.
* **Validasi Input:** *Service* (seperti `schedule_service.py`) sekarang mencakup validasi input yang kuat di *foreground* (misalnya untuk `RRULE`), yang menolak data buruk dari klien dengan `HTTP 400` alih-alih menyebabkan *crash* pada *background job*.
* **Logging Audit:** Semua *service* CUD (Create, Update, Delete) di fitur Kalender sekarang memanggil `await log_action(...)`, dan *bug* `await` di `audit_service.py` telah diperbaiki.


# Project Status: Implementasi Penuh v0.4.3 (backend\app\todos\Rencana Canvas Real-Time & Kolaboratif.md) - Fitur Backend

Sesi ini berhasil menyelesaikan implementasi backend penuh dari blueprint Potentia v0.4.3. Arsitektur telah distabilkan, diskalakan untuk 1 Juta Pengguna, dan semua 18 endpoint fungsional kini telah diimplementasikan dan berjalan.

## 1. Fitur Kolaborasi Real-Time (Skala 1 Juta Pengguna)

Sistem "Canvas Party" (edit bersama) sekarang berfungsi penuh dan mampu menangani skala besar (Goal G4).

* **Arsitektur Scalable (H1):** Koneksi WebSocket (`/ws/canvas/{id}`) tidak lagi terbatas pada satu server. Sistem ini sekarang menggunakan arsitektur **Redis Pub/Sub** yang memungkinkan penskalaan horizontal ke ribuan koneksi bersamaan. Jika 100 pengguna berada di satu canvas, mereka semua akan menerima pembaruan secara instan, tidak peduli di server mana mereka terhubung.
    
* **HTTP Fallback (H2, H3):** Jika koneksi WebSocket gagal, aplikasi sekarang memiliki endpoint HTTP (`/mutate` dan `/presence`) sebagai *fallback*. Ini memastikan pengguna tetap dapat mengedit, bahkan di jaringan yang tidak stabil (Goal G1).

## 2. API Penuh (18/18 Endpoint Selesai)

Seluruh 18 endpoint dari blueprint v0.4.3 kini telah diimplementasikan, menyediakan fungsionalitas CRUD penuh atas semua *resource*.

* **Manajemen Canvas (A4, A5, A6, A7):** Pengguna dapat membuat (`POST /canvas`), mendaftar (`GET /canvas`), memperbarui (`PATCH /canvas/{id}` untuk judul/ikon), dan mengarsipkan (`DELETE /canvas/{id}`) canvas.
* **Manajemen Konten (A1, A2, A3):** Pengguna dapat mengambil data canvas penuh (`GET /canvas/{id}`), daftar blok yang dipaginasi (`GET /canvas/{id}/blocks`), dan data blok individual (`GET /canvas/{id}/blocks/{block_id}`).
* **Manajemen Akses (A8):** Endpoint baru (`GET /canvas/{id}/permissions`) memungkinkan frontend untuk segera memeriksa role pengguna (misalnya, `can_write: true`) dan melihat daftar anggota lain di canvas.

## 3. Konsistensi, Performa, dan Ketahanan Data

Arsitektur database telah diselesaikan untuk memastikan konsistensi dan efisiensi biaya.

* **True Optimistic Locking (G2):** Sistem tidak lagi menggunakan `ot_service` yang membingungkan. Fungsionalitas edit sekarang secara eksklusif menggunakan **Optimistic Locking**. RPC atomik (`rpc_upsert_block_atomic.sql`) akan menolak editan dengan versi yang salah (mengirim `HTTP 409 Conflict`), dan frontend (TODO 26) bertanggung jawab untuk menangani konflik tersebut.
* **LexoRank Efisien (G7):** Algoritma pengurutan blok (`lexorank_service.py`) telah diganti total. Implementasi *float-based* yang boros telah diganti dengan algoritma **base-62 (Jira-style)**. Ini secara drastis mengurangi frekuensi *rebalance* database, menghemat biaya I/O, dan memenuhi Goal G7.
* **Rebalance Otomatis (TODO 24):** `RebalanceWorker` sekarang terhubung dengan benar ke database menggunakan `asyncpg`. Ketika string LexoRank menjadi terlalu panjang, trigger akan secara otomatis memanggil worker untuk merapikan data secara *real-time*.
* **Resilient Embedding (TODO 30):** `EmbeddingWorker` kini dilengkapi dengan **Circuit Breaker**. Jika API Google Gemini gagal, worker tidak akan *crash*; ia akan berhenti sejenak dan mencoba lagi nanti, melindungi antrian job.
* **Koneksi Database Skala Penuh (TODO 32):** Arsitektur sekarang dikonfigurasi untuk **PgBouncer**. Ini memungkinkan aplikasi untuk menangani ribuan koneksi simultan (G4) tanpa membebani batas koneksi database Supabase.
    

## 4. Observability & Audit (Siap Produksi)

Sistem ini sekarang siap untuk dipantau di lingkungan produksi.

* **Audit Penuh (G5):** Semua mutasi data (membuat, mengedit, menghapus blok) sekarang dicatat dengan benar ke tabel `SystemAudit` (bukan `AuditLog`), sesuai dengan blueprint.
* **Metrics Akurat (S1):** Endpoint `/metrics` sekarang secara akurat menghitung *semua* koneksi WebSocket aktif dari Redis, bukan hanya dari satu server.
* **Tracing (G6):** OpenTelemetry (TODO 35) telah diimplementasikan di `main.py`, memberikan visibilitas penuh atas performa request.

---

## 5. Ringkasan Endpoint Fungsional (18/18)

| Kategori | Endpoint | Fungsi | Status |
| :--- | :--- | :--- | :--- |
| **Real-time** | **H1:** `GET /ws/canvas/{id}` | Koneksi utama untuk kolaborasi real-time. | ✅ **Selesai & Skalabel** |
| **Real-time** | **H2:** `POST /canvas/{id}/mutate` | Fallback HTTP untuk mengirim editan blok. | ✅ **Selesai** |
| **Real-time** | **H3:** `POST /canvas/{id}/presence` | Fallback HTTP untuk mengirim posisi kursor. | ✅ **Selesai** |
| **Real-time** | **H4:** `GET /.../snapshot` | (Diimplementasikan sebagai gabungan A1 + A2). | ✅ **Selesai** |
| **Real-time** | **H5:** `POST /auth/refresh` | Refresh token JWT. | ✅ **Selesai** |
| **Real-time** | **H6:** `POST /canvas/{id}/leave` | Memberi tahu server user keluar (via HTTP). | ✅ **Selesai** |
| **AJAX** | **A1:** `GET /canvas/{id}` | Mengambil detail info satu canvas. | ✅ **Selesai** |
| **AJAX** | **A2:** `GET /canvas/{id}/blocks` | Mengambil daftar blok di dalam canvas (paginasi). | ✅ **Selesai** |
| **AJAX** | **A3:** `GET /canvas/{id}/blocks/{id}` | Mengambil data satu blok spesifik. | ✅ **Selesai** |
| **AJAX** | **A4:** `GET /canvas` | Mengambil daftar semua canvas milik pengguna. | ✅ **Selesai** |
| **AJAX** | **A5:** `POST /canvas` | Membuat canvas baru (personal atau workspace). | ✅ **Selesai** |
| **AJAX** | **A6:** `PATCH /canvas/{id}` | Memperbarui info canvas (judul, ikon, dll). | ✅ **Selesai** |
| **AJAX** | **A7:** `DELETE /canvas/{id}` | Mengarsipkan canvas (`is_archived=true`). | ✅ **Selesai** |
| **AJAX** | **A8:** `GET /canvas/{id}/permissions`| Mengecek izin tulis (`can_write`) & daftar anggota. | ✅ **Selesai** |
| **Mikro** | **M1:** `GET /health` | Liveness probe (server hidup). | ✅ **Selesai** |
| **Mikro** | **M2:** `GET /ready` | Readiness probe (DB & Redis terhubung). | ✅ **Selesai** |
| **Mikro** | **M3:** `POST /debug/echo` | Endpoint debug. | ✅ **Selesai** |
| **Mikro** | **S1:** `GET /metrics` | Endpoint Prometheus (sekarang akurat). | ✅ **Selesai** |