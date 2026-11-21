from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field


class ServiceComponentStatus(BaseModel):
    status: str = Field(description="Component operational status: healthy or degraded")
    details: Optional[str] = Field(default=None, description="Detailed component message")


class HealthCheckResponse(BaseModel):
    status: str = Field(description="Overall system health status", json_schema_extra={"example": "healthy"})
    app_name: str = Field(description="Application title", json_schema_extra={"example": "Smart Document Processing and Management System"})
    version: str = Field(description="Application version", json_schema_extra={"example": "1.0.0"})
    environment: str = Field(description="Active environment", json_schema_extra={"example": "development"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: Dict[str, ServiceComponentStatus] = Field(description="Subsystems health check")
