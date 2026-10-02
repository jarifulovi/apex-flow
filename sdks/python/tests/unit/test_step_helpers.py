import pytest
from apex_flow_sdk import validate_response, NonRetryableError


def test_validate_response_success_dict():
    payload = {"success": True, "data": "valid"}
    result = validate_response(payload)
    assert result == payload


def test_validate_response_silent_error_raises_value_error():
    payload = {"success": False, "error": "Quota exceeded"}
    with pytest.raises(ValueError) as exc_info:
        validate_response(payload)
    assert "Quota exceeded" in str(exc_info.value)


def test_validate_response_silent_error_raises_non_retryable():
    payload = {"success": False, "error": "Invalid API key"}
    with pytest.raises(NonRetryableError) as exc_info:
        validate_response(payload, raise_non_retryable=True)
    assert "Invalid API key" in str(exc_info.value)


def test_validate_response_http_object():
    class DummyResponse:
        status_code = 503
        text = "Service Unavailable"

    with pytest.raises(ValueError) as exc_info:
        validate_response(DummyResponse())
    assert "HTTP Error 503" in str(exc_info.value)
