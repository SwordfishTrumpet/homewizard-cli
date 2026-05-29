"""Pydantic models for /api/v1/system response."""

from pydantic import BaseModel


class SystemResponse(BaseModel):
    """System settings response."""

    cloud_enabled: bool
