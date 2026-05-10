"""
Shared pytest configurations.

Defines reusable fixtures for tests.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.adapters.email_adapter import EmailAdapter
from app.adapters.logger_adapter import LoggerAdapter
from app.adapters.repository import PortfolioRepository
from app.entities.experience import ProfessionalExperience
from app.entities.formation import AcademicFormation
from app.entities.project import Project
from app.main import app


@pytest.fixture
def client():
    """Fixture to provide an application TestClient."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def repository_mock() -> PortfolioRepository:
    """
    Mock of PortfolioRepository.

    Returns:
        Mock configured with sample data.
    """
    mock = AsyncMock(spec=PortfolioRepository)

    # Mock get_about
    mock.get_about.return_value = {
        "name": "Test Silva",
        "title": "Developer",
        "location": "São Paulo, SP",
        "email": "test@example.com",
        "phone": "(11) 99999-9999",
        "github": "https://github.com/test",
        "linkedin": "https://linkedin.com/in/test",
        "description": {
            "pt": "Descrição de teste",
            "en": "Test description",
            "es": "Descripción de prueba",
        },
        "availability": {"pt": "Remoto", "en": "Remote", "es": "Remoto"},
    }

    # Mock check_health
    mock.check_health.return_value = {
        "status": "ok",
        "details": "Mock Database connected",
    }

    # Mock get_projects
    mock.get_projects.return_value = [
        Project(
            id="project-1",
            name="Project A",
            short_description={
                "pt": "Project em destaque",
                "en": "Featured project",
                "es": "Proyecto destacado",
            },
            full_description={
                "pt": "Descrição completa A",
                "en": "Full description A",
                "es": "Descripción completa A",
            },
            technologies=["Python"],
            features=["Feature 1"],
            learnings=["Learning 1"],
            repository="https://github.com/test/a",
            demo=None,
            highlighted=True,
            image=None,
        ),
        Project(
            id="project-2",
            name="Project B",
            short_description={
                "pt": "Project normal",
                "en": "Normal project",
                "es": "Proyecto normal",
            },
            full_description={
                "pt": "Descrição completa B",
                "en": "Full description B",
                "es": "Descripción completa B",
            },
            technologies=["JavaScript"],
            features=["Feature 2"],
            learnings=["Learning 2"],
            repository=None,
            demo=None,
            highlighted=False,
            image=None,
        ),
    ]

    # Mock get_project_by_id
    def get_by_id(project_id: str):
        projects = {
            "project-1": mock.get_projects.return_value[0],
            "project-2": mock.get_projects.return_value[1],
        }
        return projects.get(project_id)

    mock.get_project_by_id.side_effect = get_by_id

    # Mock get_stack
    mock.get_stack.return_value = [
        {"name": "Python", "category": "backend", "level": 4, "icon": "python"},
        {"name": "React", "category": "frontend", "level": 3, "icon": "react"},
    ]

    # Mock get_experiences
    mock.get_experiences.return_value = [
        ProfessionalExperience(
            id="exp-1",
            role="Current Dev",
            company="Company A",
            location="Remote",
            start_date=date(2023, 1, 1),
            end_date=None,
            description={
                "pt": "Trabalho atual",
                "en": "Current job",
                "es": "Trabajo actual",
            },
            technologies=["Python"],
            current=True,
        ),
        ProfessionalExperience(
            id="exp-2",
            role="Former Dev",
            company="Company B",
            location="São Paulo",
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
            description={
                "pt": "Trabalho anterior",
                "en": "Previous job",
                "es": "Trabajo anterior",
            },
            technologies=["Java"],
            current=False,
        ),
    ]

    # Mock get_formation
    mock.get_formation.return_value = [
        AcademicFormation(
            id="edu-001",
            course={
                "pt": "Tecnologia em Análise e Desenvolvimento de Sistemas",
                "en": "Associate's Degree in Systems Analysis",
                "es": "Tecnólogo en Análisis y Desarrollo",
            },
            institution="UFPR – Universidade Federal do Paraná",
            location="Curitiba, PR",
            start_date=date(2026, 2, 1),
            end_date=date(2029, 3, 6),
            description={"pt": "Em curso.", "en": "In progress.", "es": "En curso."},
            current=True,
        ),
    ]

    return mock


@pytest.fixture(scope="session")
def setup_database():
    """
    Creates and initializes a temporary SQLite database for the test session.
    """
    import os
    import tempfile

    from sqlmodel import Session, SQLModel, create_engine

    from app.adapters.sql_models import (
        ExperienceModel,
        FormationModel,
        ProjectModel,
        AboutModel,
        StackModel,
    )

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    sync_url = f"sqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_engine(sync_url)
    SQLModel.metadata.create_all(engine)

    # Populate minimum data for integration tests to pass
    with Session(engine) as session:
        session.add(
            AboutModel(
                name="Test Silva",
                title="Developer",
                location="São Paulo, SP",
                email="test@example.com",
                phone="(11) 99999-9999",
                github="https://github.com/test",
                linkedin="https://linkedin.com/in/test",
                description={
                    "pt": "Descrição",
                    "en": "Description",
                    "es": "Descripción",
                },
                availability={"pt": "Remoto", "en": "Remote", "es": "Remoto"},
            )
        )

        session.add(
            ProjectModel(
                id="project-1",
                name="Project A",
                short_description={"pt": "Curta", "en": "Short", "es": "Corta"},
                full_description={"pt": "Longa", "en": "Long", "es": "Larga"},
                technologies=["Python"],
                features=[],
                learnings=[],
                repository="https://github.com/test/a",
                demo=None,
                highlighted=True,
                image=None,
            )
        )

        session.add(
            StackModel(name="Python", category="backend", level=4, icon="python")
        )

        session.add(
            ExperienceModel(
                id="exp-1",
                role={"pt": "Dev", "en": "Dev", "es": "Dev"},
                company="Company",
                location="Remote",
                start_date=date(2023, 1, 1),
                end_date=None,
                description={"pt": "Desc", "en": "Desc", "es": "Desc"},
                technologies=["Python"],
                current=True,
            )
        )

        session.add(
            FormationModel(
                id="edu-1",
                course={"pt": "Curso", "en": "Course", "es": "Curso"},
                institution="Uni",
                location="SP",
                start_date=date(2020, 1, 1),
                end_date=date(2023, 1, 1),
                description={"pt": "Fim", "en": "End", "es": "Fin"},
                current=False,
            )
        )

        session.commit()

    yield async_url

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def email_adapter_mock() -> EmailAdapter:
    """
    Mock of EmailAdapter.

    Returns:
        Mock configured to simulate email sending.
    """
    mock = AsyncMock(spec=EmailAdapter)
    mock.send_message.return_value = True
    return mock


@pytest.fixture
def logger_mock() -> LoggerAdapter:
    """
    Mock of LoggerAdapter.

    Returns:
        Mock configured to capture logs.
    """
    mock = MagicMock(spec=LoggerAdapter)
    return mock


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Resets global state (Rate Limiter, Idempotency) before each test.
    This prevents tests from accumulating limits or cache from each other.
    """
    from app.core.idempotency import store
    from app.core.rate_limit import limiter
    from app.core.spam_store import spam_dedup_store
    from app.controllers.chaos import chaos_state

    # Clear chaos state
    chaos_state.reset()

    # Clear idempotency caches
    if hasattr(store, "_cache"):
        store._cache.clear()

    # Clear rate limiter storage (slowapi)
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
        storage_obj = limiter._storage.storage
        # MemoryStorage uses a dict
        if isinstance(storage_obj, dict):
            storage_obj.clear()
        # RedisStorage uses a redis-py client
        elif hasattr(storage_obj, "flushdb"):
            # We only flush if we are in a test environment and we really need to.
            # However, for unit tests, we usually want to avoid touching real Redis.
            # If we are here, it means Limiter was initialized with a Redis URL.
            try:
                storage_obj.flushdb()
            except Exception:
                # If Redis is down, just ignore
                pass

    if hasattr(spam_dedup_store, "_memory_store"):
        spam_dedup_store._memory_store.clear()


@pytest.fixture(autouse=True)
def override_dependencies(setup_database):
    """
    Overrides FastAPI dependencies to use the real temporary database.
    Clears provider caches to ensure the new SqlRepository is used.
    """
    from app.adapters.sql_repository import SqlRepository
    from app.use_cases import (
        GetExperiencesUseCase,
        GetFormationUseCase,
        GetProjectByIdUseCase,
        GetProjectsUseCase,
        GetAboutUseCase,
        GetStackUseCase,
    )
    from app.controllers import dependencies

    repo_real_test = SqlRepository(database_url=setup_database)

    # Override individual providers
    app.dependency_overrides[dependencies.get_repository] = lambda: repo_real_test

    app.dependency_overrides[dependencies.dep_about] = lambda: GetAboutUseCase(
        repo_real_test
    )

    app.dependency_overrides[dependencies.dep_projects] = lambda: GetProjectsUseCase(
        repo_real_test
    )

    app.dependency_overrides[dependencies.dep_project_by_id] = lambda: (
        GetProjectByIdUseCase(repo_real_test)
    )

    app.dependency_overrides[dependencies.dep_stack] = lambda: GetStackUseCase(
        repo_real_test
    )

    app.dependency_overrides[dependencies.dep_experiences] = lambda: (
        GetExperiencesUseCase(repo_real_test)
    )

    app.dependency_overrides[dependencies.dep_formation] = lambda: GetFormationUseCase(
        repo_real_test
    )

    # Mock for email sending to avoid real calls in tests
    from app.use_cases.send_contact import SendContactUseCase

    mock_email = AsyncMock(spec=EmailAdapter)
    mock_email.send_message.return_value = True
    mock_logger = MagicMock(spec=LoggerAdapter)
    app.dependency_overrides[dependencies.get_send_contact_use_case] = lambda: (
        SendContactUseCase(mock_email, mock_logger)
    )

    # Clear caches for safety
    dependencies.get_repository.cache_clear()
    dependencies.dep_about.cache_clear()
    dependencies.dep_projects.cache_clear()
    dependencies.dep_project_by_id.cache_clear()
    dependencies.dep_stack.cache_clear()
    dependencies.dep_experiences.cache_clear()
    dependencies.dep_formation.cache_clear()

    yield
    app.dependency_overrides.clear()
