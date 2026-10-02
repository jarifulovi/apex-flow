"""
ApexFlow Core Step Helpers & Silent Error Validators
======================================================
Provides response inspection and exception helpers to automatically detect 
silent API errors (e.g. HTTP 4xx/5xx, JSON error keys) and trigger proper retries
or NonRetryableError aborts in ApexFlow steps.
"""

from typing import Any, Dict, Optional, Union
from apex_flow_sdk.core.exceptions import NonRetryableError


def validate_response(
    response: Any,
    raise_non_retryable: bool = False,
    error_key: str = "error",
    success_key: str = "success",
) -> Any:
    """
    Inspect a third-party API response or dictionary payload for silent errors.

    Raises:
        NonRetryableError: For fatal authentication/validation errors (401, 403, 422) if raise_non_retryable=True.
        ValueError: For retryable API errors (triggers SDK step retry with exponential backoff).
    """
    # 1. Handle HTTP Response objects (e.g. httpx, requests)
    if hasattr(response, "status_code"):
        status_code = getattr(response, "status_code")
        if status_code in (401, 403, 404, 422) and raise_non_retryable:
            raise NonRetryableError(
                f"Fatal HTTP Error {status_code}: {getattr(response, 'text', '')}"
            )
        if status_code >= 400:
            raise ValueError(
                f"HTTP Error {status_code}: {getattr(response, 'text', '')}"
            )

    # 2. Handle Dictionary Response Payloads
    if isinstance(response, dict):
        if success_key in response and response[success_key] is False:
            err_msg = response.get(error_key) or response.get("message") or "Operation failed"
            if raise_non_retryable:
                raise NonRetryableError(f"Silent API Error: {err_msg}")
            raise ValueError(f"Silent API Error: {err_msg}")

        if error_key in response and response[error_key]:
            err_msg = response[error_key]
            raise ValueError(f"Silent API Error: {err_msg}")

    return response
