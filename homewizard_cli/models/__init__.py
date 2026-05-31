"""Pydantic models for P1 Meter API responses."""

from .data import DataResponse, ExternalDevice
from .measurement import Measurement
from .system import SystemResponse
from .v2 import (
    BatteryState,
    DeviceInfoV2,
    MeasurementV2,
    StateResponse,
    SystemV2,
    TelegramV2,
    UserInfo,
    V2ApiInfo,
    V2Error,
    V2ExternalDevice,
)

__all__ = [
    "DataResponse",
    "ExternalDevice",
    "Measurement",
    "SystemResponse",
    "MeasurementV2",
    "SystemV2",
    "DeviceInfoV2",
    "UserInfo",
    "BatteryState",
    "StateResponse",
    "TelegramV2",
    "V2ExternalDevice",
    "V2ApiInfo",
    "V2Error",
]
