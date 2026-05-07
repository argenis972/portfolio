"""
Integration tests for SqlRepository.

Uses a temporary SQLite file to test real queries,
manual JSON serialization, and repository behavior.

Why a temporary file and not :memory:?
- SqlRepository uses an async engine (aiosqlite).
- The setup code uses a synchronous engine to seed data.
- SQLite only shares :memory: between connections on the same thread,
  so we use a temporary file that both engines can read.
"""

import os
import tempfile
from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.adapters.sql_models import (
    ExperienceModel,
    FormationModel,
    ProjectModel,
    AboutModel,
    StackModel,
)
from app.adapters.sql_repository import SqlRepository

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def seeded_repo():
    """
    Creates a SqlRepository with a temporary SQLite database populated with test data.
    The database is automatically destroyed at the end of each test.
    """
    # Create temporary file for database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    sync_url = f"sqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    try:
        # Create tables and seed with synchronous engine
        sync_engine = create_engine(sync_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(sync_engine)

        with Session(sync_engine) as session:
            _seed_database(session)
            session.commit()

        # Returns async repository pointing to the same file
        yield SqlRepository(database_url=async_url)

    finally:
        # Cleanup: remove temporary file
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _seed_database(session: Session) -> None:
    """Populates the test database with sample data."""

    session.add(
        AboutModel(
            name="Argenis Teste",
            title="Backend Developer",
            location="Curitiba, PR",
            email="teste@example.com",
            phone="(41) 99999-9999",
            github="https://github.com/teste",
            linkedin="https://linkedin.com/in/teste",
            description={
                "pt": "Descrição PT",
                "en": "Description EN",
                "es": "Descripción ES",
            },
            availability={"pt": "Remoto", "en": "Remote", "es": "Remoto"},
        )
    )

    session.add(
        ProjectModel(
            id="proj-test-1",
            name="Project Teste",
            short_description={"pt": "Curta PT", "en": "Short EN", "es": "Corta ES"},
            full_description={
                "pt": "Completa PT",
                "en": "Full EN",
                "es": "Completa ES",
            },
            technologies=["Python", "FastAPI"],
            features=["Feature A", "Feature B"],
            learnings=["Aprendizado A"],
            repository="https://github.com/teste/repo",
            demo=None,
            highlighted=True,
            image=None,
        )
    )

    session.add(
        ExperienceModel(
            id="exp-test-1",
            role={"pt": "Dev Backend", "en": "Backend Dev", "es": "Dev Backend"},
            company="Empresa Teste",
            location="Remoto",
            start_date=date(2024, 1, 1),
            end_date=None,
            description={
                "pt": "Descrição PT",
                "en": "Description EN",
                "es": "Descripción ES",
            },
            technologies=["Python", "FastAPI"],
            current=True,
        )
    )

    session.add(
        FormationModel(
            id="edu-test-1",
            course={
                "pt": "Análise de Sistemas",
                "en": "Systems Analysis",
                "es": "Análisis",
            },
            institution="UFPR Teste",
            location="Curitiba, PR",
            start_date=date(2024, 2, 1),
            end_date=date(2026, 12, 1),
            description={
                "pt": "Em andamento",
                "en": "In progress",
                "es": "En progreso",
            },
            current=True,
        )
    )

    session.add(StackModel(name="Python", category="backend", level=5, icon="python"))
    session.add(StackModel(name="FastAPI", category="backend", level=4, icon="fastapi"))
    session.add(StackModel(name="React", category="frontend", level=3, icon="react"))


# ─── Tests: check_health ───────────────────────────────────────────────────


async def test_check_health_returns_ok(seeded_repo):
    """Health check should return status 'ok' when the database is accessible."""
    result = await seeded_repo.check_health()
    assert result["status"] == "ok"


# ─── Tests: get_about ───────────────────────────────────────────────────────


async def test_get_about_returns_basic_data(seeded_repo):
    """get_about should return a dict with the model fields."""
    result = await seeded_repo.get_about()

    assert isinstance(result, dict)
    assert result["name"] == "Argenis Teste"
    assert result["email"] == "teste@example.com"
    assert result["title"] == "Backend Developer"


async def test_get_about_deserializes_description(seeded_repo):
    """The 'description' field should be deserialized from JSON string to dict."""
    result = await seeded_repo.get_about()

    assert isinstance(result["description"], dict)
    assert result["description"]["pt"] == "Descrição PT"
    assert result["description"]["en"] == "Description EN"
    assert result["description"]["es"] == "Descripción ES"


async def test_get_about_deserializes_availability(seeded_repo):
    """The 'availability' field should be deserialized from JSON string to dict."""
    result = await seeded_repo.get_about()

    assert isinstance(result["availability"], dict)
    assert result["availability"]["en"] == "Remote"


# ─── Tests: get_projects ────────────────────────────────────────────────────


async def test_get_projects_returns_list(seeded_repo):
    """get_projects should return a list of Project."""
    projects = await seeded_repo.get_projects()

    assert isinstance(projects, list)
    assert len(projects) == 1


async def test_get_projects_returns_correct_data(seeded_repo):
    """Returned project should have the correct seeded data."""
    projects = await seeded_repo.get_projects()
    p = projects[0]

    assert p.id == "proj-test-1"
    assert p.name == "Project Teste"
    assert p.highlighted is True
    assert p.repository == "https://github.com/teste/repo"
    assert p.demo is None


async def test_get_projects_deserializes_technologies(seeded_repo):
    """The 'technologies' field should be deserialized from JSON string to list."""
    projects = await seeded_repo.get_projects()
    p = projects[0]

    assert isinstance(p.technologies, list)
    assert "Python" in p.technologies
    assert "FastAPI" in p.technologies


async def test_get_projects_deserializes_short_description(seeded_repo):
    """The 'short_description' field should be deserialized to a localized dict."""
    projects = await seeded_repo.get_projects()
    p = projects[0]

    assert isinstance(p.short_description, dict)
    assert p.short_description["pt"] == "Curta PT"
    assert p.short_description["en"] == "Short EN"


async def test_get_project_by_id_found(seeded_repo):
    """Lookup by existing ID should return the project."""
    project = await seeded_repo.get_project_by_id("proj-test-1")

    assert project is not None
    assert project.id == "proj-test-1"
    assert project.name == "Project Teste"


async def test_get_project_by_id_not_found(seeded_repo):
    """Lookup by nonexistent ID should return None."""
    project = await seeded_repo.get_project_by_id("id-fantasma-999")

    assert project is None


# ─── Tests: get_stack ──────────────────────────────────────────────────────


async def test_get_stack_returns_list(seeded_repo):
    """get_stack should return a list of dicts."""
    stack = await seeded_repo.get_stack()

    assert isinstance(stack, list)
    assert len(stack) == 3


async def test_get_stack_returns_correct_fields(seeded_repo):
    """Each stack item should have the 4 expected fields."""
    stack = await seeded_repo.get_stack()

    for item in stack:
        assert "name" in item
        assert "category" in item
        assert "level" in item
        assert "icon" in item


async def test_get_stack_returns_correct_values(seeded_repo):
    """Stack should contain the inserted technologies."""
    stack = await seeded_repo.get_stack()
    names = [s["name"] for s in stack]

    assert "Python" in names
    assert "FastAPI" in names
    assert "React" in names


# ─── Tests: get_experiences ───────────────────────────────────────────────


async def test_get_experiences_returns_list(seeded_repo):
    """get_experiences should return a list of ProfessionalExperience."""
    experiences = await seeded_repo.get_experiences()

    assert isinstance(experiences, list)
    assert len(experiences) == 1


async def test_get_experiences_deserializes_role(seeded_repo):
    """The 'role' (localized) field should be deserialized to a dict."""
    experiences = await seeded_repo.get_experiences()
    exp = experiences[0]

    assert isinstance(exp.role, dict)
    assert exp.role["pt"] == "Dev Backend"
    assert exp.role["en"] == "Backend Dev"


async def test_get_experiences_deserializes_technologies(seeded_repo):
    """The 'technologies' field should be deserialized to a list."""
    experiences = await seeded_repo.get_experiences()
    exp = experiences[0]

    assert isinstance(exp.technologies, list)
    assert "Python" in exp.technologies


async def test_get_experiences_current_is_true(seeded_repo):
    """Experience marked as current should have current=True."""
    experiences = await seeded_repo.get_experiences()
    exp = experiences[0]

    assert exp.current is True
    assert exp.end_date is None


# ─── Tests: get_formation ───────────────────────────────────────────────────


async def test_get_formation_returns_list(seeded_repo):
    """get_formation should return a list of AcademicFormation."""
    formation = await seeded_repo.get_formation()

    assert isinstance(formation, list)
    assert len(formation) == 1


async def test_get_formation_deserializes_course(seeded_repo):
    """The 'course' (localized) field should be deserialized to a dict."""
    formation = await seeded_repo.get_formation()
    f = formation[0]

    assert isinstance(f.course, dict)
    assert f.course["pt"] == "Análise de Sistemas"
    assert f.course["en"] == "Systems Analysis"


async def test_get_formation_returns_correct_data(seeded_repo):
    """Formation should have the correct seeded data."""
    formation = await seeded_repo.get_formation()
    f = formation[0]

    assert f.id == "edu-test-1"
    assert f.institution == "UFPR Teste"
    assert f.current is True
