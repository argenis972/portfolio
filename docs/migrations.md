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

## 2. Migration Enforcement Reality

The backend currently does **not** run an automatic migration-head verification at startup.

This means the application can start even if pending Alembic migrations exist. Operationally, schema correctness depends on deployment discipline: migrations must be applied before rolling out code that relies on new schema changes.

## 3. Applying Migrations (Production)

To prevent race conditions, database migrations in production **must not** be executed automatically during the application startup process (especially when spinning up multiple worker replicas simultaneously).

The safe, standard flow for production deployment is:

1. **Pre-flight Migration:** The CI/CD pipeline or deployment orchestrator runs the Alembic upgrade command against the production database *before* the new application containers are deployed or rotated.
   ```bash
   alembic upgrade head
   ```
2. **Application Rollout:** Only after the database is successfully migrated to `head` are the new backend application containers deployed.
