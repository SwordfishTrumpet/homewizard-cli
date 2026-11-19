"""Client resolution and v2→v1 data conversion for homewizard-cli."""

from .client import P1Client
from .client_v2 import P1ClientV2
from .config import load_config
from .errors import InvalidOptionError
from .models import Measurement
from .models.v2 import MeasurementV2

API_VERSIONS = ["v1", "v2"]


def validate_api_version(api_version: str) -> str:
    """Return *api_version* when this build supports it, else refuse it.

    Any value other than "v2" used to fall through to the v1 client, so a
    typo such as ``--api-version V2`` silently read the meter over plain HTTP
    with no token while reporting success (issue #30).
    """
    if api_version not in API_VERSIONS:
        raise InvalidOptionError(
            f"Unknown --api-version {api_version!r}: "
            f"choose one of {', '.join(API_VERSIONS)}"
        )
    return api_version


def resolve_client(
    api_version: str,
    host: str,
    timeout: float = 3.0,
    token: str | None = None,
    verify_cert: bool = True,
    proxy: str | None = None,
) -> P1Client | P1ClientV2:
    """Return the appropriate client for the given API version.
    
    Falls back to config file values for token and no_verify.
    SSL Safety: v2 with --no-verify requires --token to prevent
    insecure unauthenticated connections.
    """
    validate_api_version(api_version)
    if api_version == "v2":
        cfg = load_config()
        if token is None and cfg.token:
            token = cfg.token
        if verify_cert and cfg.no_verify is True:
            verify_cert = False
        if not verify_cert and token is None:
            import sys
            sys.exit(
                "Error: --no-verify requires --token on API v2.\n"
                "  SSL verification disabled but no auth token provided.\n"
                "  Either provide --token or remove --no-verify."
            )
        return P1ClientV2(
            host, timeout, token=token, verify_cert=verify_cert, proxy=proxy
        )
    return P1Client(host, timeout, proxy=proxy)


def to_measurement(raw: dict | MeasurementV2, api_version: str = "v2") -> Measurement:
    """Convert raw v1/v2 data to the unified Measurement model.

    If *raw* is already a MeasurementV2, dump it to a dict first so the
    model_validator can map v2 field names.
    """
    if isinstance(raw, MeasurementV2):
        raw = raw.model_dump(exclude_none=True)
    return Measurement.model_validate(raw)


def convert_v2_measurement(m: MeasurementV2) -> Measurement:
    """Backward-compat wrapper around :func:`to_measurement`."""
    return to_measurement(m, api_version="v2")
