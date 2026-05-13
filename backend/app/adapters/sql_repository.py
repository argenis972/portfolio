"""
Repository implementation using SQLModel (SQL).
"""

from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters.sql_models import (
    ExperienceModel,
    FormationModel,
    ProjectModel,
    AboutModel,
    StackModel,
)
from app.adapters.repository import PortfolioRepository
from app.core.infrastructure import register_engine
from app.settings import settings
from app.entities.experience import ProfessionalExperience
from app.entities.formation import AcademicFormation
from app.entities.philosophy import PhilosophyInspiration
from app.entities.project import Project


class SqlRepository(PortfolioRepository):
    """
    PortfolioRepository implementation using SQLModel.

    Connects to a SQL database (e.g., SQLite, PostgreSQL).
    """

    def __init__(self, database_url: str = settings.database_url):
        """
        Initializes the SQL repository.

        Args:
            database_url: Database connection URL.
        """
        engine_kwargs: dict[str, Any] = {}
        if not database_url.startswith("sqlite"):
            engine_kwargs.update(
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_recycle=settings.db_pool_recycle_seconds,
                pool_timeout=settings.db_pool_timeout_seconds,
                pool_use_lifo=settings.db_pool_use_lifo,
                pool_pre_ping=True,
                connect_args={
                    "timeout": settings.db_connect_timeout_seconds,
                    "command_timeout": settings.db_command_timeout_seconds,
                    "server_settings": {"application_name": settings.app_name},
                },
            )

        self.engine = create_async_engine(database_url, **engine_kwargs)
        register_engine(self.engine)  # Register for graceful shutdown via lifespan
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def check_health(self) -> dict:
        """
        Verifies if the database connection is active.
        """
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ok", "details": "SQL database connected"}
        except Exception as e:
            return {"status": "error", "details": f"SQL connection failed: {str(e)}"}

    async def get_about(self) -> dict:
        """
        Gets About section information from the database.
        """
        async with self.session_factory() as session:
            statement = select(AboutModel)
            result = await session.exec(statement)
            model = result.first()
            if not model:
                return {}
            # Return as dict to maintain use case compatibility
            data = model.model_dump()
            data.pop("id", None)
            return data

    async def get_projects(self) -> List[Project]:
        """
        Gets all projects from the database.
        """
        async with self.session_factory() as session:
            statement = select(ProjectModel)
            result = await session.exec(statement)
            models = result.all()
            return [
                Project(
                    id=m.id,
                    name=m.name,
                    short_description=m.short_description,
                    full_description=m.full_description,
                    technologies=m.technologies,
                    features=m.features,
                    learnings=m.learnings,
                    repository=m.repository,
                    demo=m.demo,
                    highlighted=m.highlighted,
                    image=m.image,
                )
                for m in models
            ]

    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """
        Searches for a specific project by ID.
        """
        async with self.session_factory() as session:
            statement = select(ProjectModel).where(ProjectModel.id == project_id)
            result = await session.exec(statement)
            m = result.first()
            if not m:
                return None
            return Project(
                id=m.id,
                name=m.name,
                short_description=m.short_description,
                full_description=m.full_description,
                technologies=m.technologies,
                features=m.features,
                learnings=m.learnings,
                repository=m.repository,
                demo=m.demo,
                highlighted=m.highlighted,
                image=m.image,
            )

    async def get_stack(self) -> List[dict]:
        """
        Gets tech stack from the database.
        """
        async with self.session_factory() as session:
            statement = select(StackModel)
            result = await session.exec(statement)
            models = result.all()
            return [
                {
                    "name": m.name,
                    "category": m.category,
                    "level": m.level,
                    "icon": m.icon,
                }
                for m in models
            ]

    async def get_experiences(self) -> List[ProfessionalExperience]:
        """
        Gets professional experiences from the database.
        """
        async with self.session_factory() as session:
            statement = select(ExperienceModel).order_by(
                col(ExperienceModel.start_date).desc()
            )
            result = await session.exec(statement)
            models = result.all()
            return [
                ProfessionalExperience(
                    id=m.id,
                    role=m.role,
                    company=m.company,
                    location=m.location,
                    start_date=m.start_date,
                    end_date=m.end_date,
                    description=m.description,
                    technologies=m.technologies,
                    current=m.current,
                )
                for m in models
            ]

    async def get_formation(self) -> List[AcademicFormation]:
        """
        Gets academic formations from the database.
        """
        async with self.session_factory() as session:
            statement = select(FormationModel).order_by(
                col(FormationModel.start_date).desc()
            )
            result = await session.exec(statement)
            models = result.all()
            return [
                AcademicFormation(
                    id=m.id,
                    course=m.course,
                    institution=m.institution,
                    location=m.location,
                    start_date=m.start_date,
                    end_date=m.end_date,
                    description=m.description,
                    current=m.current,
                )
                for m in models
            ]

    async def get_philosophy(self) -> List[PhilosophyInspiration]:
        """
        Philosophy is static JSON data. Not implemented in SQL.
        """
        return []
