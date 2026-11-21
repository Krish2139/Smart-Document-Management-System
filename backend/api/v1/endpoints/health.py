from fastapi import APIRouter, status, Response
from backend.schemas.health import HealthCheckResponse
from backend.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="System Health Check",
    description="Inspects database and storage connectivity and returns overall operational status."
)
def get_health(response: Response) -> HealthCheckResponse:
    health_data = HealthService.get_system_health()
    if health_data.status != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health_data
