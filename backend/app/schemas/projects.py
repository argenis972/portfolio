"""
Schemas for /api/projects and /api/projects/{id} endpoints.

Defines contracts for project listing and details.
"""

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.base_types import LocalizedText


class ProjectSummary(BaseModel):
    """
    Project summary for listing.

    Used in GET /api/projects endpoint.
    """

    id: str = Field(
        ...,
        examples=["portfolio-api"],
        description="Project unique identifier",
    )
    name: str = Field(
        ...,
        max_length=100,
        examples=["Portfolio API"],
        description="Project name",
    )
    short_description: LocalizedText = Field(
        ...,
        description="Brief project description in PT, EN and ES",
    )
    full_description: LocalizedText | None = Field(
        default=None,
        description="Full story description (Problem/Constraint/Decision/Trade-off/Impact) in PT, EN and ES",
    )
    technologies: list[str] = Field(
        ...,
        examples=[["Python", "FastAPI", "Pydantic"]],
        description="Technologies used",
    )
    features: list[str] = Field(
        default_factory=list,
        description="Main features or capabilities of the project",
    )
    highlighted: bool = Field(
        default=False,
        description="Whether the project should be highlighted",
    )
    repository: HttpUrl | None = Field(
        default=None,
        examples=["https://github.com/Argenis1412/portfolio"],
        description="Repository URL",
    )
    demo: HttpUrl | None = Field(
        default=None,
        examples=["https://portfolio-api.railway.app"],
        description="Live demo URL",
    )
    image: HttpUrl | None = Field(
        default=None,
        description="Cover image URL",
    )


class DetailedProject(BaseModel):
    """
    Full project details.

    Used in GET /api/projects/{id} endpoint.
    """

    id: str = Field(
        ...,
        examples=["portfolio-api"],
        description="Project unique identifier",
    )
    name: str = Field(
        ...,
        max_length=100,
        examples=["Portfolio API"],
        description="Project name",
    )
    short_description: LocalizedText = Field(
        ...,
        description="Brief project description in PT, EN and ES",
    )
    full_description: LocalizedText = Field(
        ...,
        description="Full project description in PT, EN and ES",
    )
    technologies: list[str] = Field(
        ...,
        examples=[["Python", "FastAPI", "Pydantic", "Pytest"]],
        description="Technologies used",
    )
    features: list[str] = Field(
        ...,
        examples=[["Health check", "Project CRUD", "Validation"]],
        description="Main features",
    )
    learnings: list[str] = Field(
        ...,
        examples=[["Clean Architecture", "Unit testing"]],
        description="Key learnings from the project",
    )
    repository: HttpUrl | None = Field(
        default=None,
        examples=["https://github.com/Argenis1412/portfolio"],
        description="Repository URL",
    )
    demo: HttpUrl | None = Field(
        default=None,
        examples=["https://portfolio-api.railway.app"],
        description="Live demo URL",
    )
    highlighted: bool = Field(
        default=False,
        description="Whether the project should be highlighted",
    )
    image: HttpUrl | None = Field(
        default=None,
        description="Cover image URL",
    )


class ProjectsResponse(BaseModel):
    """
    Project list response.

    Attributes:
        projects: List of summarized projects.
        total: Total number of projects.
    """

    projects: list[ProjectSummary] = Field(
        ...,
        description="List of projects",
    )
    total: int = Field(
        ...,
        ge=0,
        examples=[3],
        description="Total number of projects",
    )
