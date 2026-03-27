import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_transfer():
    base_url = "https://api.flutterwave.com/v3"
    secret_key = os.getenv("FLUTTERWAVE_SECRET_KEY")
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "account_bank": "058",
        "account_number": "0498565176",
        "amount": 100,
        "currency": "NGN",
        "narration": "Test Withdrawal",
        "reference": "TEST-REF-" + os.urandom(4).hex(),
        "debit_currency": "NGN",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/transfers", json=payload, headers=headers
            )
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_transfer())
