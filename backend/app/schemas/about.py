"""
Schemas for /api/about endpoint.

Defines the response contract with personal information of the developer.
"""

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.schemas.base_types import LocalizedText


class AboutResponse(BaseModel):
    """
    Personal information for "About Me" section.

    Attributes:
        name: Developer's full name.
        title: Professional title.
        location: City and state.
        email: Contact email.
        phone: Contact phone.
        github: GitHub profile URL.
        linkedin: LinkedIn profile URL.
        description: Professional summary (internationalized).
        availability: Work availability preference (internationalized).
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Argenis Lopez"],
        description="Full name",
    )
    title: str = Field(
        ...,
        max_length=200,
        examples=["Backend Developer | Python | FastAPI"],
        description="Professional title",
    )
    location: str = Field(
        ...,
        max_length=100,
        examples=["Curitiba, PR"],
        description="Current location",
    )
    email: EmailStr = Field(
        ...,
        examples=["argenisbackend@gmail.com"],
        description="Contact email",
    )
    phone: str = Field(
        ...,
        max_length=20,
        examples=["(41) 9 9510-3364"],
        description="Contact phone",
    )
    github: HttpUrl = Field(
        ...,
        examples=["https://github.com/Argenis1412"],
        description="GitHub profile URL",
    )
    linkedin: HttpUrl = Field(
        ...,
        examples=["https://linkedin.com/in/argenis972"],
        description="LinkedIn profile URL",
    )
    description: LocalizedText = Field(
        ...,
        description="Professional summary in PT, EN and ES",
    )
    availability: LocalizedText = Field(
        ...,
        description="Work availability preference in PT, EN and ES",
    )
