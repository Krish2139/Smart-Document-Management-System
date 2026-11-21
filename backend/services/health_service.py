from backend.config.settings import settings
from backend.database.session import check_db_connection
from backend.storage import get_storage_provider
from backend.schemas.health import HealthCheckResponse, ServiceComponentStatus


class HealthService:
    """Service responsible for validating the readiness of all system dependencies."""

    @staticmethod
    def get_system_health() -> HealthCheckResponse:
        db_healthy = check_db_connection()
        storage_provider = get_storage_provider()
        storage_healthy = storage_provider.check_health()

        components = {
            "database": ServiceComponentStatus(
                status="healthy" if db_healthy else "degraded",
                details="SQLite connected and responsive" if db_healthy else "Unable to query SQLite database"
            ),
            "storage": ServiceComponentStatus(
                status="healthy" if storage_healthy else "degraded",
                details=f"{settings.STORAGE_TYPE.capitalize()} storage writable and verified"
                if storage_healthy else f"{settings.STORAGE_TYPE.capitalize()} storage inaccessible"
            )
        }

        overall_status = "healthy" if (db_healthy and storage_healthy) else "degraded"

        return HealthCheckResponse(
            status=overall_status,
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.APP_ENV,
            components=components
        )
