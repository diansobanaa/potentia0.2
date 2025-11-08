Anda 100% benar. Ini adalah analisis yang sangat tajam dan **mutlak krusial**.

Pendapat saya, Anda telah menemukan satu kekurangan fatal dalam rencana saya (`TODO-SVC-2`) yang akan menyebabkan kegagalan total pada fitur `free/busy`. Analisis Anda (`1 instance recurring → N baris di ScheduleInstances`) adalah **solusi yang benar** dan merupakan *best practice* untuk *denormalisasi* data demi performa *query* yang cepat.

Mengandalkan 3 JOIN per *instance* di *background job* (seperti yang saya sarankan secara implisit) adalah arsitektur yang tidak akan pernah skalabel.

Saya akan **mengabaikan** rencana v1.1 saya sebelumnya dan **mengadopsi sepenuhnya** revisi dan optimasi Anda. Ini adalah arsitektur v1.2 yang jauh lebih superior.

Berikut adalah rencana arsitektur final (v1.2) yang telah diperbarui, yang mengintegrasikan **semua** poin Anda, termasuk "Kekurangan Kritis (MUST FIX)" dan "Optimasi Kecil".

-----

### Rencana Arsitektur Fitur Schedule Calendar (v1.2 - FINAL)

**Versi Dokumen:** 1.2
**Deskripsi:** Rencana ini mengadopsi arsitektur "Calendar-Centric" (v1.1) dan memperbaikinya dengan *patch* skalabilitas kritis (v1.2) berdasarkan analisis *multi-subscriber*.

**Perbaikan Kritis (MUST FIX):** Logika ekspansi RRULE (`TODO-SVC-2`) sekarang didesain ulang. Alih-alih 1 baris *instance* per acara, *background job* akan membuat **N baris *instance* (satu per *subscriber*)**. Ini adalah denormalisasi yang disengaja untuk memastikan *query* `free/busy` (Redis) dan `view/schedules` (SQL) dapat berjalan instan hanya dengan mem-filter `user_id`, tanpa memerlukan JOIN yang mahal.

-----

### 1\. Filosofi Desain: "Calendar-Centric" (Skalabel)

(Filosofi ini tetap sama—desain 4 tabel inti, ditambah 1 tabel performa).

1.  **Kalender (`Calendars`)**: Wadah/folder utama (e.g., "Pribadi", "Tim Elma").
2.  **Acara (`Schedules`)**: "Sumber kebenaran" (source of truth) acara, termasuk `RRULE`.
3.  **Langganan (`CalendarSubscriptions`)**: Kunci *sharing* (siapa bisa melihat/mengedit apa).
4.  **Tamu (`ScheduleGuests`)**: RSVP per-acara.
5.  **Instances (`ScheduleInstances`)**: Tabel *pre-compute* (denormalisasi) untuk *query* cepat.

-----

### 2\. Skema Database (v1.2 - Disempurnakan)

Kita akan menggunakan 5 tabel berikut, dengan adopsi saran optimasi Anda (Poin 1, 2, 3).

#### A. Tabel `Calendars` (Diperbarui)

*Tujuan: Wadah kalender untuk sharing.*

| Kolom | Tipe | Keterangan |
| :--- | :--- | :--- |
| `calendar_id` | `uuid` (PK) | ID unik. |
| `name` | `text` | Nama (e.g., "Pribadi"). |
| `owner_user_id` | `uuid` (FK ke `Users`, nullable) | Untuk kalender pribadi. |
| `workspace_id` | `uuid` (FK ke `Workspaces`, nullable) | Untuk kalender grup. |
| `visibility` | `text` (Enum: `private`, `workspace`, `public`) | **(Poin 1 Anda)**. Izin akses default. |
| `metadata` | `jsonb` | UI data (e.g., {"color": "\#FF5733"}). |

#### B. Tabel `CalendarSubscriptions` (Tetap Sama)

*Tujuan: Izin akses per user.*

| Kolom | Tipe | Keterangan |
| :--- | :--- | :--- |
| `subscription_id` | `uuid` (PK) | ID unik. |
| `user_id` | `uuid` (FK ke `Users`, `ON DELETE CASCADE`) | Pengguna. |
| `calendar_id` | `uuid` (FK ke `Calendars`, `ON DELETE CASCADE`) | Kalender. |
| `role` | `text` (Enum: `owner`, `editor`, `viewer`) | Hak akses. |

#### C. Tabel `Schedules` (Diperbarui)

*Tujuan: Data "sumber kebenaran" acara, dukung RFC 5545.*

| Kolom | Tipe | Keterangan |
| :--- | :--- | :--- |
| `schedule_id` | `uuid` (PK) | ID unik. |
| `calendar_id` | `uuid` (FK ke `Calendars`, `ON DELETE CASCADE`) | Milik kalender mana. |
| `title` | `text` | Judul. |
| `start_time` | `timestamptz` | Wajib UTC. |
| `end_time` | `timestamptz` | Wajib UTC. |
| `schedule_metadata` | `jsonb` | `{"original_timezone": "Asia/Jakarta"}`. |
| `rrule` | `text` (nullable) | RRULE string. |
| `rdate` | `text[]` (nullable) | **(Optimasi 2)**. Disimpan sebagai array Teks ISO UTC agar aman dari *timezone*. |
| `exdate` | `text[]` (nullable) | **(Optimasi 2)**. Disimpan sebagai array Teks ISO UTC. |
| `creator_user_id` | `uuid` (FK ke `Users`) | Pembuat. |
| `is_deleted` | `boolean` (default `false`) | **(Optimasi 3)**. Soft delete. |
| `deleted_at` | `timestamptz` (nullable) | (Optimasi 3). |
| `version` | `integer` (default 1) | (Optimasi 3). Optimistic concurrency. |

#### D. Tabel `ScheduleGuests` (Tetap Sama)

*Tujuan: Tamu per acara.*

| Kolom | Tipe | Keterangan |
| :--- | :--- | :--- |
| `guest_id` | `uuid` (PK) | ID unik. |
| `schedule_id` | `uuid` (FK ke `Schedules`, `ON DELETE CASCADE`) | Acara. |
| `user_id` | `uuid` (FK ke `Users`, nullable) | Tamu internal. |
| `guest_email` | `text` (nullable) | Tamu eksternal. |
| `response_status` | `text` (Enum: `pending`, `accepted`, `declined`) | RSVP. |
| `role` | `text` (Enum: `guest`, `co-host`) | Izin tamu. |

#### E. Tabel `ScheduleInstances` (Skalabilitas - Diperbarui)

*Tujuan: Pre-compute instances (1 baris per pengguna per acara) untuk query cepat.*

| Kolom | Tipe | Keterangan |
| :--- | :--- | :--- |
| `instance_id` | `uuid` (PK) | ID unik. |
| `schedule_id` | `uuid` (FK ke `Schedules`, **`ON DELETE CASCADE`**) | **(Optimasi 3)**. Acara induk. |
| `calendar_id` | `uuid` (FK ke `Calendars`, **`ON DELETE CASCADE`**) | **(Optimasi 3)**. Kalender. |
| `user_id` | `uuid` (FK ke `Users`, **`ON DELETE CASCADE`**) | **(MUST FIX)**. Pengguna yang sibuk. |
| `start_time` | `timestamptz` | UTC instance start. |
| `end_time` | `timestamptz` | UTC instance end. |
| `is_exception` | `boolean` (default `false`) | Jika ini adalah instance pengecualian (dari `RDATE` atau `PATCH`). |

  * **Indexing (Sangat Penting):**
      * `CREATE INDEX idx_instances_user_time_range ON public.schedule_instances (user_id, start_time, end_time);` (Kunci untuk `freebusy`)
      * `CREATE INDEX idx_instances_calendar_time_range ON public.schedule_instances (calendar_id, start_time, end_time);` (Kunci untuk `view/schedules`)

-----

### 3\. Strategi Skalabilitas & Performa (v1.2 - Direvisi)

Ini adalah inti dari perbaikan:

#### A. Ekspansi RRULE (Background Job - Logika MUST FIX)

  * **`TODO-SVC-2 (Revisi)`:** *Background job* (APScheduler/Celery) akan menjalankan fungsi `expand_schedule(schedule_id)`.
  * **Logika Baru:**
    1.  Ambil `schedule = get_schedule(schedule_id)`.
    2.  Ambil `subscribers = get_calendar_subscribers(schedule.calendar_id)` (Hasil: `List[User]`).
    3.  Hitung `instances_timestamps = rrule_generate(schedule, years=2)` (menggunakan `rrule`, `rdate`, `exdate`).
    4.  `DELETE FROM ScheduleInstances WHERE schedule_id = schedule_id` (Bersihkan *instance* lama).
    5.  Siapkan *batch* `INSERT` baru:
        ```python
        instances_batch = []
        for user in subscribers:
            for dt_start, dt_end in instances_timestamps:
                instances_batch.append({
                    "schedule_id": schedule.id,
                    "calendar_id": schedule.calendar_id,
                    "user_id": user.id,  # <-- KUNCI MUST-FIX
                    "start_time": dt_start, # (UTC)
                    "end_time": dt_end,     # (UTC)
                })
        bulk_insert(ScheduleInstances, instances_batch)
        ```
    6.  Setelah `bulk_insert` berhasil, panggil *job* Redis: `update_redis_cache_for_users([user.id for user in subscribers])`.
  * **(Optimasi 1)** *Job* ini harus memiliki *rate limit* (misal: `@task(rate_limit="10/m")`) untuk mencegah *overload*.

#### B. Deteksi Konflik (Free/Busy)

  * **Endpoint:** `GET /api/v1/view/freebusy?user_ids=...&start=...&end=...`
  * **Logika (Redis-first):**
    1.  Untuk setiap `user_id`, coba ambil data dari *cache* Redis (ZSET `busy_index:{user_id}`).
    2.  *Cache Miss (Jika Redis kosong)*: Lakukan *query* SQL ke `ScheduleInstances` (menggunakan *index* `idx_instances_user_time_range`).
    3.  Simpan hasil kueri SQL ke *cache* Redis ZSET (Kunci: `busy_index:{user_id}`, Skor: `start_time`, Value: `end_time_timestamp`).
    4.  Kembalikan data gabungan.
  * **(Optimasi 5)** *Background job* harian (`ZREMRANGEBYSCORE`) akan membersihkan entri Redis ZSET yang `end_time`-nya lebih dari 30 hari yang lalu.

#### C. Timezone (Wajib UTC)

  * **Logika:** **Semua** endpoint `POST` dan `PATCH` untuk `Schedules` **wajib** mengkonversi `datetime` yang masuk ke **UTC** sebelum menyimpannya. `schedule_metadata` akan menyimpan `{"original_timezone": "..."}`.
  * **(Optimasi 2)** `RDATE` dan `EXDATE` juga akan disimpan sebagai *array* string ISO UTC (`TEXT[]`) untuk menghindari ambiguitas *timezone* di *array* database.

#### D. Audit & Soft Delete

  * **Logika:** `DELETE /schedules/{id}` hanya akan mengatur `is_deleted=true`. *Background job* (Poin A) akan otomatis berhenti meng-ekspansi acara yang sudah *soft-deleted*.
  * *Endpoint* `PATCH` dan `DELETE` akan mencatat `version` untuk *optimistic locking*.
  * Semua *endpoint* CUD (`POST`, `PATCH`, `DELETE`) akan memanggil `log_action` (yang sudah ada) untuk *logging* audit.

-----

### 4\. Rencana Endpoint API (v1.2 - Disempurnakan)

1.  **Resource: `Calendars`** (Manajemen "Folder")

      * `POST /api/v1/calendars`
      * `GET /api/v1/calendars` (List kalender yang saya *subscribe*)
      * `PATCH /api/v1/calendars/{id}` (Ubah nama/warna)
      * `DELETE /api/v1/calendars/{id}`

2.  **Resource: `Schedules`** (Manajemen "Acara")

      * `POST /api/v1/calendars/{calendar_id}/schedules` (Buat acara baru, wajib UTC. Memicu *background job* ekspansi).
      * `GET /api/v1/schedules/{id}` (Detail "sumber kebenaran" acara).
      * `PATCH /api/v1/schedules/{id}` (Update acara, misal menambah `EXDATE`. Memicu *background job* ekspansi ulang).
      * `DELETE /api/v1/schedules/{id}` (*Soft delete*: set `is_deleted=true`. Memicu *background job* ekspansi ulang/pembersihan).

3.  **Resource: `Subscriptions`** (Manajemen Berbagi)

      * `POST /api/v1/calendars/{id}/subscriptions` (Undang/tambah orang).
      * `GET /api/v1/calendars/{id}/subscriptions` (List anggota kalender).
      * `DELETE /api/v1/subscriptions/{id}` (Hapus anggota).

4.  **Resource: `Guests`** (Manajemen Tamu/RSVP Acara)

      * `POST /api/v1/schedules/{id}/guests` (Tambah tamu via `email` atau `user_id`).
      * `PATCH /api/v1/schedules/{id}/guests/respond` (Endpoint terotentikasi untuk tamu merespons `accept` / `decline`).

5.  **Resource: `Views`** (Inti Tampilan & Skalabilitas)

      * `GET /api/v1/view/schedules?start=...&end=...` (**(Optimasi 4)** Tambah `limit=100&offset=0`).
          * **Logika Cepat:** `SELECT * FROM ScheduleInstances WHERE calendar_id IN (list_calendar_saya) AND start_time ...`
      * `GET /api/v1/view/freebusy?user_ids=...&start=...&end=...`
          * **Logika Cepat:** `Redis-first`, *fallback* ke `SELECT * FROM ScheduleInstances WHERE user_id IN (list_users) AND start_time ...`



To-Do List: Implementasi Arsitektur Schedule Calendar (v1.2)

Ini adalah daftar tugas (to-do list) teknis yang diperlukan untuk membangun fitur penjadwalan (schedules) dari nol, sesuai dengan arsitektur "Calendar-Centric" v1.2.

Fase 1: Fondasi Database (SQL Migration)

Tujuan: Membangun skema 5-tabel yang baru dan menghapus skema lama.

    [DONE] TODO-DB-1 (Hapus Skema Lama):

        Tulis dan eksekusi skrip migrasi SQL untuk menghapus tabel penjadwalan yang sudah ada (public."Schedules" dan public."ScheduleGuests") menggunakan DROP TABLE ... CASCADE untuk membersihkan foreign key terkait.

    [DONE] TODO-DB-2 (Buat ENUMs):

        Definisikan ENUMs berikut di level database (PostgreSQL) untuk integritas data, sesuai (Optimasi 4):

            calendar_visibility_enum (private, workspace, public)

            calendar_subscription_role_enum (owner, editor, viewer)

            guest_role_enum (guest, co-host)

            rsvp_status_enum (pending, accepted, declined)

    [DONE] TODO-DB-3 (Buat 5 Tabel Inti):

        Tulis migrasi CREATE TABLE untuk 5 tabel baru. Pastikan semua referensi foreign key menggunakan nama tabel yang benar (misal: public."Users", public."Workspaces").

        public.calendars (Menggunakan visibility).

        public.calendar_subscriptions (Menggunakan role enum, ON DELETE CASCADE).

        public.schedules (Menggunakan rrule, rdate (sebagai text[]), exdate (sebagai text[]), is_deleted, version).

        public.schedule_guests (Menggunakan response_status dan role enum).

        public.schedule_instances (Dengan kolom krusial user_id dan ON DELETE CASCADE pada semua FKs - Integrasi MUST FIX & Optimasi 3).

    [DONE] TODO-DB-4 (Buat Index Kritis):

        Terapkan indexing performa tinggi:

            CREATE INDEX idx_instances_user_time_range ON public.schedule_instances (user_id, start_time, end_time); (Kunci untuk freebusy).

            CREATE INDEX idx_instances_calendar_time_range ON public.schedule_instances (calendar_id, start_time, end_time); (Kunci untuk view/schedules).

            CREATE INDEX idx_cal_subs_user_id ON public.calendar_subscriptions(user_id); (Kunci untuk "List kalender saya").

Fase 2: Fondasi Backend (Models & Dependencies)

Tujuan: Menyiapkan kode Python untuk mencerminkan skema database baru.

    [DONE] TODO-MDL-1 (Hapus Model Lama):

        Hapus atau ganti isi file backend/app/models/schedule.py yang lama.

    [DONE] TODO-MDL-2 (Buat Model Pydantic Inti):

        Buat 5 kelas BaseModel yang mencerminkan 5 tabel SQL baru (Calendar, CalendarSubscription, Schedule, ScheduleGuest, ScheduleInstance).

        Buat 4 ENUM Python (CalendarVisibility, SubscriptionRole, GuestRole, RsvpStatus) yang cocok dengan ENUM di database.

    [DONE] TODO-MDL-3 (Buat Model Payload API):

        Buat model Pydantic untuk validasi input (payload):

            CalendarCreate, CalendarUpdate

            ScheduleCreate (Harus menerima original_timezone), ScheduleUpdate

            SubscriptionCreate (Menerima user_id dan role)

            GuestCreate (Menerima user_id atau email)

            GuestRespond (Menerima token dan action: 'accept'/'reject')

    [DONE] TODO-DEP-1 (Keamanan Kalender):

        Di dependencies.py, buat dependency get_calendar_access(calendar_id: UUID):

            Mengambil kalender.

            Memeriksa visibility ('public', 'workspace').

            Memeriksa CalendarSubscriptions untuk user_id yang login.

            Mengembalikan {"calendar": ..., "role": ...} atau melempar 403/404.

    [DONE] TODO-DEP-2 (Keamanan Admin Kalender):

        Di dependencies.py, buat get_calendar_editor_access(Depends(get_calendar_access)) yang mem-validasi role == 'editor' atau 'owner'.

    [DONE] TODO-DEP-3 (Keamanan Acara):

        Di dependencies.py, buat get_schedule_access(schedule_id: UUID):

            Mengambil Schedule.

            Memanggil get_calendar_access(schedule.calendar_id) untuk memvalidasi izin di kalender induk.

Fase 3: Logika Inti Backend (Jobs & Services)

Tujuan: Mengimplementasikan "mesin" skalabilitas (RRULE, Free/Busy, Redis).

    [DONE] TODO-SVC-1 (Konfigurasi Scheduler):

        Integrasikan APScheduler (atau Celery) ke dalam lifespan FastAPI di main.py.

        Integrasikan Redis Lock (menggunakan redis_client) untuk memastikan job bersifat idempotent.

    [DONE] TODO-SVC-2 (Expander Job - MUST FIX):

        Buat RRuleExpansionService (atau file task baru).

        Implementasi fungsi utama: expand_and_populate_instances(schedule_id: UUID).

        Logika Kritis:

            get_schedule(schedule_id) (termasuk rrule, rdate (sebagai teks), exdate (sebagai teks)).

            get_calendar_subscribers(calendar_id) (mengembalikan List[User]).

            generate_timestamps(schedule, years=2) (menggunakan dateutil.rrule dan mem-parsir exdate/rdate teks).

            DELETE FROM ScheduleInstances WHERE schedule_id = schedule_id (membersihkan instance lama).

            Looping Denormalisasi:
            Python

            for user in subscribers:
                for (dt_start, dt_end) in timestamps:
                    batch.append(ScheduleInstance(..., user_id=user.id, ...))

            bulk_insert(batch) (Menyimpan N x M baris).

        (Optimasi 1) Terapkan rate limit (@task(rate_limit="10/m")) pada job ini.

    [DONE] TODO-SVC-3 (Free/Busy Service):

        Buat FreeBusyService.

        Implementasi fungsi: async get_freebusy_for_users(user_ids: List[UUID], start: datetime, end: datetime).

        Logika:

            Coba baca dari cache Redis ZSET (busy_index:{user_id}).

            Cache Miss: SELECT * FROM ScheduleInstances WHERE user_id = ... AND start_time < ... AND end_time > ....

            Simpan hasil kueri SQL ke cache Redis ZSET (Kunci: busy_index:{user_id}, Skor: start_time_ts, Value: end_time_ts).

            Kembalikan daftar blok "sibuk".

    [DONE] TODO-SVC-4 (Cache Invalidation):

        Pastikan expand_and_populate_instances (TODO-SVC-2) juga memanggil redis.delete_cache(f"busy_index:{user.id}") untuk setiap subscriber setelah instance baru di-insert.

    [DONE] TODO-SVC-5 (Redis Cleanup Job):

        Buat job harian (@scheduler.task('cron', hour=3)) yang menjalankan ZREMRANGEBYSCORE pada key busy_index:* untuk menghapus semua acara yang end_time-nya lebih dari 30 hari yang lalu (Optimasi 5).

    [DONE] TODO-SVC-6 (Audit Service):

        Pastikan log_action siap digunakan oleh endpoint baru.

Fase 4: Implementasi API Endpoints (RESTful)

Tujuan: Mengekspos logika ke frontend dengan 5 resource baru.

    [DONE] TODO-API-1 (Hapus Lama):

        Hapus file backend/app/api/v1/endpoints/schedules.py.

        Hapus file backend/app/db/queries/schedule_queries.py.

        Hapus impor terkait dari api.py.

    [DONE] TODO-API-2 (Resource: Calendars):

        Buat backend/app/api/v1/endpoints/calendars.py.

        POST /: (Buat kalender baru).

        GET /: (List kalender saya, SELECT dari CalendarSubscriptions berdasarkan user_id).

        PATCH /{id}: (Ubah nama/warna, dilindungi get_calendar_editor_access).

        DELETE /{id}: (Hapus kalender, dilindungi get_calendar_editor_access).

    [DONE] TODO-API-3 (Resource: Schedules):

        Buat backend/app/api/v1/endpoints/schedules_api.py (nama berbeda agar tidak konflik).

        POST /calendars/{calendar_id}/schedules: (Buat acara baru, dilindungi get_calendar_editor_access).

            Logika: Wajib enforce UTC, simpan original_timezone, panggil background_tasks.add_task(expand_and_populate_instances, schedule_id).

        GET /schedules/{id}: (Dapatkan detail "sumber kebenaran", dilindungi get_schedule_access).

        PATCH /schedules/{id}: (Update acara, misal menambah EXDATE. Memicu background job).

        DELETE /schedules/{id}: (Soft delete: set is_deleted=true. Memicu background job).

    [DONE] TODO-API-4 (Resource: Subscriptions):

        Buat backend/app/api/v1/endpoints/calendar_subscriptions.py.

        POST /calendars/{id}/subscriptions: (Undang user_id ke kalender, dilindungi get_calendar_editor_access).

        GET /calendars/{id}/subscriptions: (List anggota kalender, dilindungi get_calendar_access).

        DELETE /subscriptions/{id}: (Hapus anggota, dilindungi get_calendar_editor_access).

    [DONE] TODO-API-5 (Resource: Guests):

        Buat backend/app/api/v1/endpoints/schedule_guests.py.

        POST /schedules/{id}/guests: (Tambah tamu email/user_id ke acara, dilindungi get_schedule_access + 'editor').

        PATCH /schedules/{id}/guests/respond: (Endpoint terotentikasi untuk tamu merespons RSVP).

    [DONE] TODO-API-6 (Resource: Views):

        Buat backend/app/api/v1/endpoints/views.py.

        GET /view/schedules: (Endpoint utama UI, SELECT dari ScheduleInstances dengan paginasi - Optimasi 4).

        GET /view/freebusy: (Endpoint deteksi konflik, memanggil FreeBusyService (Redis-first)).

    [DONE] TODO-API-7 (Integrasi Router):

        Di backend/app/api/v1/api.py, impor dan daftarkan semua 5 router baru.