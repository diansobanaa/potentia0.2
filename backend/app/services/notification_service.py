import aiosmtplib
from email.message import EmailMessage
from app.core.config import settings

async def send_schedule_email(user_email: str, schedule_data: dict):
    if not settings.SMTP_HOST:
        print("SMTP not configured. Skipping email.")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_USER
    message["To"] = user_email
    message["Subject"] = f"Jadwal Baru Dibuat: {schedule_data['title']}"
    message.set_content(f"Hai, jadwal baru telah dibuat untuk Anda:\n\n{schedule_data['title']}\nWaktu: {schedule_data['start_time']}")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
        )
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


