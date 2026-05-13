"""
Dependency providers for HTTP controllers.

Centralizes the composition of adapters and use cases for use with FastAPI Depends.
"""

from functools import lru_cache

from app.adapters.email_adapter import (
    EmailAdapter,
    ConsoleEmailAdapter,
    ResendEmailAdapter,
)
from app.adapters.logger_adapter import StructuredLogger
from app.adapters.repository import PortfolioRepository, JsonRepository
from app.adapters.sql_repository import SqlRepository
from app.use_cases.get_about import GetAboutUseCase
from app.use_cases.get_projects import GetProjectsUseCase, GetProjectByIdUseCase
from app.use_cases.get_stack import GetStackUseCase
from app.use_cases.get_experiences import GetExperiencesUseCase
from app.use_cases.get_formation import GetFormationUseCase
from app.use_cases.get_philosophy import GetPhilosophyUseCase
from app.use_cases.send_contact import SendContactUseCase
from app.core.queue import JobQueue, queue
from app.settings import settings


@lru_cache
def get_job_queue() -> JobQueue | None:
    """Returns the job queue provider (Redis Streams)."""
    return queue


@lru_cache
def get_static_repository() -> PortfolioRepository:
    """Returns shared data repository for JSON static reading."""
    return JsonRepository()


@lru_cache
def get_repository() -> PortfolioRepository:
    """Returns transactional repository (SQL) for forms and rate limits."""
    return SqlRepository()


@lru_cache
def dep_about() -> GetAboutUseCase:
    """Returns use case for about section."""
    return GetAboutUseCase(get_static_repository())


@lru_cache
def dep_projects() -> GetProjectsUseCase:
    """Returns use case for projects listing."""
    return GetProjectsUseCase(get_static_repository())


@lru_cache
def dep_project_by_id() -> GetProjectByIdUseCase:
    """Returns use case for project details."""
    return GetProjectByIdUseCase(get_static_repository())


@lru_cache
def dep_stack() -> GetStackUseCase:
    """Returns use case for technical stack."""
    return GetStackUseCase(get_static_repository())


@lru_cache
def dep_experiences() -> GetExperiencesUseCase:
    """Returns use case for professional experiences."""
    return GetExperiencesUseCase(get_static_repository())


@lru_cache
def dep_formation() -> GetFormationUseCase:
    """Returns use case for academic formations."""
    return GetFormationUseCase(get_static_repository())


@lru_cache
def dep_philosophy() -> GetPhilosophyUseCase:
    """Returns use case for philosophical principles."""
    return GetPhilosophyUseCase(get_static_repository())


@lru_cache
def get_send_contact_use_case() -> SendContactUseCase:
    """Returns use case for sending contact messages."""
    email_adapter: EmailAdapter

    # Priority 1: Resend (Production and professional)
    if settings.resend_api_key.strip():
        email_adapter = ResendEmailAdapter(
            settings.resend_api_key,
            settings.resend_from_email,
            settings.resend_to_email,
        )
    # Priority 2: Console (Fallback / Local development)
    else:
        email_adapter = ConsoleEmailAdapter()

    logger = StructuredLogger()
    return SendContactUseCase(email_adapter, logger)
