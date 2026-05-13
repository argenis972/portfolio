"""
Schemas for POST /api/contact endpoint.

Defines request and response contracts for message submission.
"""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

NAME_REGEX = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .,'-]{1,79}$")
SUBJECT_REGEX = re.compile(r"^[A-Za-zÀ-ÿ0-9 .,:;!?()/#&+@'\-]{0,120}$")


class ContactRequest(BaseModel):
    """
    Contact form data.

    Validations:
        - name: 2-80 characters
        - email: valid format
        - message: 1-3000 characters
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        examples=["Maria Silva"],
        description="Sender name",
    )
    email: EmailStr = Field(
        ...,
        min_length=3,
        max_length=100,
        examples=["maria@empresa.com"],
        description="Reply-to email",
    )
    subject: Optional[str] = Field(
        default="Contact via Portfolio",
        min_length=0,
        max_length=120,
        examples=["Job opportunity"],
        description="Message subject",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        examples=["Hello, I saw your portfolio and would like to talk..."],
        description="Message content",
    )
    # Honeypot fields (should be empty)
    website: Optional[str] = Field(None, description="Honeypot 1")
    fax: Optional[str] = Field(None, description="Honeypot 2")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Sanitizes the name, allowing it to fail silently in the guard."""
        return re.sub(r"\s+", " ", value).strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Lowercase and strip email for consistent dedup/rate-limit keying."""
        return value.strip().lower()

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: Optional[str]) -> Optional[str]:
        """Sanitizes the subject, allowing it to fail silently in the guard."""
        if value is None:
            return value
        return re.sub(r"\s+", " ", value).strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Sanitizes the message, allowing it to fail silently in the guard."""
        return re.sub(r"\s+", " ", value).strip()


class ContactResponse(BaseModel):
    """
    Response after sending a message.

    Attributes:
        success: Whether the message was successfully queued.
        message: Result description.
    """

    success: bool = Field(
        ...,
        examples=[True],
        description="Whether the submission was successful",
    )
    message: str = Field(
        ...,
        examples=["Message sent successfully!"],
        description="Result description",
    )
    queue_status: str = Field(
        default="queued",
        examples=["queued"],
        description="Queue/processing status exposed to the client",
    )
    delivery_mode: str = Field(
        default="background",
        examples=["background"],
        description="How delivery is processed after acceptance",
    )
    downstream: str = Field(
        default="email_adapter",
        examples=["formspree"],
        description="Downstream provider or adapter selected by the backend",
    )
