"""
Adapters for external services.

Responsibility:
- Abstract external dependencies (APIs, storage, logs)
- Allow easy implementation swaps
- Isolate business logic from technical details

Pattern: Interface (ABC) + Concrete implementation.
"""

from app.adapters.email_adapter import (
    EmailAdapter,
    ResendEmailAdapter,
)
from app.adapters.logger_adapter import LoggerAdapter, StructuredLogger
from app.adapters.repository import JsonRepository, PortfolioRepository
from app.adapters.sql_repository import SqlRepository

__all__ = [
    "EmailAdapter",
    "ResendEmailAdapter",
    "PortfolioRepository",
    "JsonRepository",
    "SqlRepository",
    "LoggerAdapter",
    "StructuredLogger",
]
