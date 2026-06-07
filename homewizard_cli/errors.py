"""Error types and exit codes for homewizard-cli."""

from .util import _dumps_json


class P1Error(Exception):
    """Base error with exit code."""

    def __init__(self, message: str, code: int = 1, details: str | None = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

    def to_json(self) -> str:
        """Return error as JSON string."""
        error_dict = {"error": self.message, "code": self.code}
        if self.details:
            error_dict["details"] = self.details
        return _dumps_json(error_dict)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\n  {self.details}"
        return self.message


class DeviceNotFoundError(P1Error):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, code=2, details=details)


class HttpError(P1Error):
    def __init__(self, status: int, url: str):
        self.status = status
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


class UnsupportedError(P1Error):
    """Device does not support this feature (exit code 8)."""

    def __init__(self, message: str):
        super().__init__(message, code=8)


class UntilConditionMetError(P1Error):
    def __init__(self, message: str):
        super().__init__(message, code=10)
