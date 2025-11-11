# Panduan Gaya Penulisan SQL Proyek Potentia

Dokumen ini adalah "sumber kebenaran" (source of truth) untuk semua interaksi database (SQL dan Python) di proyek Potentia. Tujuannya adalah untuk memastikan konsistensi penuh setelah standarisasi skema.

## Aturan Emas: Konvensi Nama Tabel

Semua tabel, terlepas dari asalnya (Core, Canvas v0.4.3, Chat v2, Calendar v1.2), **WAJIB** menggunakan format `lowercase_snake_case`.

Nama `PascalCase` (misalnya `"Users"`, `"Canvas"`, `"Blocks"`) sudah **usang (obsolete)** dan telah dimigrasikan.

### Daftar Tabel Aktif (Contoh)

Selalu gunakan nama-nama `lowercase_snake_case` ini:

| Modul | Nama Tabel Standar |
| :--- | :--- |
| **Core** | `public.users` |
| | `public.workspaces` |
| | `public.workspace_members` |
| | `public.workspace_invitations` |
| **Canvas** | `public.canvas` |
| | `public.canvas_access` |
| | `public.blocks` |
| | `public.block_operations` |
| **Sistem** | `public.system_audit` (dan partisinya) |
| | `public.system_prompts` |
| | `public.embedding_job_queue` |
| **Chat** | `public.conversations` |
| | `public.context` |
| | `public.messages` |
| | `public.summary_memory` |
| | `public.user_preferences` |
| | `public.user_semantic_memories` |
| | `public.decision_logs` |
| **Kalender**| `public.calendars` |
| | `public.calendar_subscriptions` |
| | `public.schedules` |
| | `public.schedule_guests` |
| | `public.schedule_instances` |

---

## Aturan Penulisan Kueri

### 1. Di dalam Kode Python (File `.py`)

Klien Supabase Python (`.table("nama_tabel")`) secara otomatis menambahkan tanda kutip (`""`). Tugas Anda adalah **memastikan string di dalam `.table()` sama persis** dengan nama tabel `lowercase_snake_case` di database.

* **BENAR:**
    ```python
    client.table("users").select("*")
    client.table("canvas").select("*")
    client.table("blocks").select("*")
    client.table("block_operations").select("*")
    client.table("system_audit").select("*")
    ```

* **SALAH (Akan Gagal):**
    ```python
    client.table("Users").select("*")  # ERROR: relation "public.Users" does not exist
    client.table("Canvas").select("*")  # ERROR: relation "public.Canvas" does not exist
    client.table("Blocks").select("*")  # ERROR: relation "public.Blocks" does not exist
    ```

### 2. Di dalam File `.sql` (RPCs, Migrasi)

Saat menulis SQL mentah, Anda **harus** menggunakan nama `lowercase_snake_case`.

Karena nama-nama ini tidak mengandung huruf besar, penggunaan tanda kutip ganda (`""`) bersifat **opsional**, namun disarankan untuk konsistensi.

* **BENAR (Disarankan):**
    ```sql
    INSERT INTO public.blocks (canvas_id, ...) ...
    SELECT * FROM public.system_audit WHERE ...
    ```

* **BENAR (Juga Diterima):**
    ```sql
    INSERT INTO public."blocks" (canvas_id, ...) ...
    SELECT * FROM public."system_audit" WHERE ...
    ```

* **SALAH (Akan Gagal):**
    ```sql
    INSERT INTO public."Blocks" ... -- ERROR: relation "public.Blocks" does not exist
    SELECT * FROM public.Canvas ... -- ERROR: relation "public.canvas" does not exist (PostgreSQL melipagandakan 'canvas')
    ```

## Anda bisa menemukan Schema Database terbaru di: backend/app/db/schema.sql
## Anda bisa menemukan Migrasi Database terbaru di: backend/app/db/migrations/
## Anda bisa menemukan Kueri RPC terbaru di: backend/app/db/rpcs/