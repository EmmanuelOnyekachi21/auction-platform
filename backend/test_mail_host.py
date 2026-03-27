import asyncio
import os

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

load_dotenv()

# EXPERIMENT: Try standard smtp.mailtrap.io
config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "test@example.com"),
    MAIL_PORT=2525,
    MAIL_SERVER="smtp.mailtrap.io",  # Changed host
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "Test"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
)


async def test_mail():
    message = MessageSchema(
        subject="Fastapi-Mail test (Internal Hostname Test)",
        recipients=["test@example.com"],
        body="Hello world",
        subtype=MessageType.plain,
    )
    fm = FastMail(config)
    try:
        await fm.send_message(message)
        print("Success on smtp.mailtrap.io!")
    except Exception as e:
        print(f"Failed on smtp.mailtrap.io: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_mail())
