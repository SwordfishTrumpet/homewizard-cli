"""Error types and exit codes for homewizard-cli."""

import json
from typing import Optional


class P1Error(Exception):
    """Base error with exit code."""

    def __init__(self, message: str, code: int = 1, details: Optional[str] = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

    def to_json(self) -> str:
        """Return error as JSON string."""
        error_dict = {"error": self.message, "code": self.code}
        if self.details:
            error_dict["details"] = self.details
        return json.dumps(error_dict)

    def __str__(self) -> str:
        if self.details:
            return f"Error: {self.message}\n  {self.details}"
        return f"Error: {self.message}"


class DeviceNotFoundError(P1Error):
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, code=2, details=details)


class HttpError(P1Error):
    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} from {url}", code=3)


class TimeoutError(P1Error):
    def __init__(self, timeout: float):
        super().__init__(f"Timeout after {timeout}s", code=4)


class ParseError(P1Error):
    def __init__(self, message: str):
        super().__init__(message, code=5)


class CrcMismatchError(P1Error):
    def __init__(self, expected: str, actual: str):
        super().__init__(f"CRC mismatch: expected {expected}, got {actual}", code=6)


class WriteError(P1Error):
    def __init__(self, message: str):
        super().__init__(message, code=7)


class UntilConditionMet(P1Error):
    def __init__(self, message: str):
        super().__init__(message, code=10)
