"""
Adapter for sending emails.

Abstract interface + implementation with Resend.
"""

from abc import ABC, abstractmethod

import httpx
import structlog


from app.entities.message import Message
from app.utils.email import mask_email

logger = structlog.get_logger(__name__)


class EmailAdapter(ABC):
    """
    Abstract interface for sending emails.

    Allows easy implementation swaps (Resend → SendGrid → SES).
    """

    @abstractmethod
    async def send_message(self, message: Message) -> bool:
        """
        Sends an email message.

        Args:
            message: Message to be sent.

        Returns:
            bool: True if sent successfully, False otherwise.
        """
        pass



class ResendEmailAdapter(EmailAdapter):
    """
    EmailAdapter implementation using Resend API.
    """

    def __init__(self, api_key: str, from_email: str, to_email: str):
        self._api_key = api_key
        self._from_email = from_email
        self._to_email = to_email
        self._configured = bool(api_key and api_key.strip())
        self._url = "https://api.resend.com/emails"

    async def send_message(self, message: Message) -> bool:
        if not self._configured:
            logger.warning("resend_not_configured", reason="RESEND_API_KEY is empty")
            return False

        try:
            # Prepare basic HTML message
            html_content = f"""
            <h3>New Contact from Portfolio</h3>
            <p><strong>Name:</strong> {message.name}</p>
            <p><strong>Email:</strong> {message.email}</p>
            <p><strong>Subject:</strong> {message.subject}</p>
            <p><strong>Message:</strong></p>
            <div style="white-space: pre-wrap; background: #f4f4f4; padding: 15px; border-radius: 5px;">
                {message.message}
            </div>
            """

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self._from_email
                        if "<" in self._from_email
                        else f"Portfolio <{self._from_email}>",
                        "to": self._to_email or self._from_email,
                        "subject": message.subject,
                        "reply_to": message.email,
                        "html": html_content,
                    },
                )

                success = response.status_code in (200, 201)
                if success:
                    logger.info("resend_send_success", id=response.json().get("id"))
                else:
                    logger.warning(
                        "resend_send_failure",
                        status=response.status_code,
                        body=response.text,
                    )
                return success

        except Exception as e:
            logger.error("resend_unexpected_error", error=str(e), exc_info=True)
            return False


class ConsoleEmailAdapter(EmailAdapter):
    """
    Fallback adapter that just logs the message to the console.

    Useful for local development when no email service is configured.
    """

    async def send_message(self, message: Message) -> bool:
        """
        Logs the message to the console in a structured way.

        Args:
            message: Message to be 'sent'.

        Returns:
            bool: Always True.
        """
        logger.info(
            "contact_received_console",
            name=message.name,
            email=mask_email(message.email),
            subject=message.subject,
            message_length=len(message.message),
            status="intercepted_by_console",
        )
        return True
