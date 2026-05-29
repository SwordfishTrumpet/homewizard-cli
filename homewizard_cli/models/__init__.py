"""Pydantic models for P1 Meter API responses."""

from .data import DataResponse, ExternalDevice
from .system import SystemResponse
from .v2 import (
    MeasurementV2,
    SystemV2,
    DeviceInfoV2,
    UserInfo,
    BatteryState,
    TelegramV2,
    V2ExternalDevice,
    V2ApiInfo,
    V2Error,
)

__all__ = [
    "DataResponse",
    "ExternalDevice",
    "SystemResponse",
    "MeasurementV2",
    "SystemV2",
    "DeviceInfoV2",
    "UserInfo",
    "BatteryState",
    "TelegramV2",
    "V2ExternalDevice",
    "V2ApiInfo",
    "V2Error",
]
