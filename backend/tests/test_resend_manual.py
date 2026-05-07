import asyncio
import os
import sys

# Add root directory to path to allow importing app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters.email_adapter import ResendEmailAdapter
from app.settings import settings
from app.entities.message import Message


async def test_resend_connection():
    """
    Manual test to verify if Resend is properly configured.
    """
    print("\nStarting Resend test...")

    api_key = settings.resend_api_key
    from_email = settings.resend_from_email
    to_email = settings.resend_to_email

    if not api_key or "your_api_key" in api_key:
        print("ERROR: configure RESEND_API_KEY in the .env file")
        return

    print(f"Using API Key: {api_key[:6]}...{api_key[-4:]}")
    print(f"From: {from_email}")
    print(f"To: {to_email}")

    adapter = ResendEmailAdapter(api_key, from_email, to_email)

    test_message = Message(
        name="Argenis Test",
        email="test@example.com",
        subject="System Test - Resend Live",
        message="If you received this, your Resend and Cloudflare configuration works perfectly!",
    )

    print("Sending test email...")
    success = await adapter.send_message(test_message)

    if success:
        print("SUCCESS! The email was sent as per the Resend log.")
    else:
        print("FAILURE: Could not send the email.")


if __name__ == "__main__":
    # Ensure compatibility with Windows and Python 3.10+
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_resend_connection())
