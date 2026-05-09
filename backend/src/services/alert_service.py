"""Alert service.

Currently a thin wrapper over the repository. It exists for two reasons:

  * Symmetry with FileService keeps the API layer's dependency shape
    uniform — every router talks to a service, not sometimes a service
    and sometimes a repository.
  * Future alert-creation rules (deduplication, rate limiting,
    fan-out to external systems) have an obvious home.

We are not adding ceremony just to have it: when this stays a one-liner,
removing it later is a 5-minute refactor. The cost of keeping it now is
near-zero.
"""

from __future__ import annotations

from src.domain.models import Alert
from src.repositories.alert_repository import AlertRepository


class AlertService:
    def __init__(self, repository: AlertRepository) -> None:
        self._repository = repository

    async def list_alerts(self) -> list[Alert]:
        return await self._repository.list_all()
