"""Alert endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_alert_service
from src.api.schemas import AlertItem
from src.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertItem])
async def list_alerts(
    alert_service: AlertService = Depends(get_alert_service),
) -> list[AlertItem]:
    alerts = await alert_service.list_alerts()
    return [AlertItem.model_validate(a) for a in alerts]
