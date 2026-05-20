# Database Migration Guide

This document outlines the standard operating procedure for managing database schema changes using Alembic within the Portfolio platform.

## 1. Generating Migrations (Local Development)

Whenever you modify a SQLAlchemy model (e.g., inside `backend/app/models/`), you must generate an Alembic revision to reflect those changes in the database schema.

1. Ensure your local database is running and accessible (via Docker or local instance).
2. From the `backend` directory, run the auto-generation command:
   ```bash
   alembic revision --autogenerate -m "description_of_change"
   ```
3. **Crucial:** Always review the generated migration file inside `backend/alembic/versions/`. Alembic's `--autogenerate` feature is powerful but not infallible (e.g., it may misinterpret table renames as a drop and create, or struggle with certain enum modifications).

## 2. Lifespan Schema Validation

The FastAPI backend is designed to fail fast if the database schema is out of sync with the application's models.

During the startup lifespan event (`backend/app/main.py`), the application automatically checks the current migration head. If there are pending migrations that have not been applied to the database, the application will log a critical error and immediately shut down. This protective mechanism guarantees that application code expecting a new schema never runs against a stale database.

## 3. Applying Migrations (Production)

To prevent race conditions, database migrations in production **must not** be executed automatically during the application startup process (especially when spinning up multiple worker replicas simultaneously).

The safe, standard flow for production deployment is:

1. **Pre-flight Migration:** The CI/CD pipeline or deployment orchestrator runs the Alembic upgrade command against the production database *before* the new application containers are deployed or rotated.
   ```bash
   alembic upgrade head
   ```
2. **Application Rollout:** Only after the database is successfully migrated to `head` are the new backend application containers deployed.
3. **Lifespan Verification:** As the new containers start, the lifespan schema validation verifies that the database matches the models, passes the check, and allows the application to begin serving traffic safely.
