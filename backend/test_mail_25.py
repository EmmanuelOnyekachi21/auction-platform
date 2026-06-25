import asyncio
import os

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

load_dotenv()

# EXPERIMENT: Try PORT 25 with NO TLS
config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "test@example.com"),
    MAIL_PORT=25,
    MAIL_SERVER=os.getenv("MAIL_SERVER", "sandbox.smtp.mailtrap.io"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "Test"),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
)


async def test_mail():
    message = MessageSchema(
        subject="Fastapi-Mail test (Plain Port 25)",
        recipients=["test@example.com"],
        body="Hello world via 25",
        subtype=MessageType.plain,
    )
    fm = FastMail(config)
    try:
        await fm.send_message(message)
        print("Success on 25!")
    except Exception as e:
        print(f"Failed on 25: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_mail())
