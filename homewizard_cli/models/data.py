"""Backward-compat alias — Measurement is the canonical data type."""

from .measurement import ExternalDevice
from .measurement import Measurement as DataResponse

__all__ = ["DataResponse", "ExternalDevice"]
