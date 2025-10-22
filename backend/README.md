# AI Collaborative Canvas Backend (MVP v0.1)

Backend API untuk aplikasi canvas kolaboratif dengan AI Agent yang cerdas.

## Fitur

- Manajemen Workspace & Canvas (Tim & Pribadi)
- Konten berbasis Blocks
- AI Agent dengan Role-Playing & Memory
- Schedules terintegrasi
- Audit Log
- Sistem Autentikasi 4 Tingkat (Guest, User, Pro, Admin)
- Rate Limiting yang skalabel dengan Redis

## Setup

1.  **Clone repo**
2.  **Buat file `.env`** dari `.env.example` dan isi variabel lingkungan.
3.  **Setup Database**: Jalankan skema SQL final di editor SQL Supabase Anda.
4.  **Jalankan dengan Docker**: Cara termudah untuk menjalankan backend dan Redis bersama-sama.
    ```bash
    docker-compose up --build
    ```
    Aplikasi akan berjalan di `http://localhost:8000` dan Redis di `localhost:6379`.

## Arsitektur

- **Framework**: FastAPI
- **Database/Auth**: Supabase (PostgreSQL + pgvector)
- **AI**: Google Gemini
- **Rate Limiting**: Redis
- **Otomasi**: Library Python (APScheduler, aiosmtplib)