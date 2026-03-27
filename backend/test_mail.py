import asyncio
import os

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

load_dotenv()

config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "test@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 2525)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "sandbox.smtp.mailtrap.io"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "Test"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
)


async def test_mail():
    message = MessageSchema(
        subject="Fastapi-Mail test",
        recipients=["test@example.com"],
        body="Hello world",
        subtype=MessageType.plain,
    )
    fm = FastMail(config)
    try:
        await fm.send_message(message)
        print("Success!")
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_mail())
