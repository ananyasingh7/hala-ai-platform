import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from services.notifications.discord import send_discord_message

def write_markdown(output_dir: str, filename: str, content: str) -> str:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    full_path = path / filename
    full_path.write_text(content, encoding="utf-8")
    return str(full_path)


def send_email(subject: str, content: str) -> Optional[str]:
    host = os.getenv("NEWSLETTER_SMTP_HOST")
    port = int(os.getenv("NEWSLETTER_SMTP_PORT", "587"))
    user = os.getenv("NEWSLETTER_SMTP_USER")
    password = os.getenv("NEWSLETTER_SMTP_PASSWORD")
    sender = os.getenv("NEWSLETTER_EMAIL_FROM")
    recipient = os.getenv("NEWSLETTER_EMAIL_TO")

    if not host or not sender or not recipient:
        return None

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(content)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(message)
    return recipient


async def send_discord(content: str) -> bool:
    return await send_discord_message(content)
