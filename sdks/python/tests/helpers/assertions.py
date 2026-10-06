import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union


def parse_datetime(val: Union[str, datetime]) -> datetime:
    """Safely parse ISO 8601 string or datetime object into UTC datetime."""
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, str):
        cleaned = val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise ValueError(f"Cannot parse '{val}' as datetime")


def assert_timestamp_within_range(
    actual: Optional[Union[str, datetime]],
    expected: Union[str, datetime, bool],
    tolerance_seconds: float = 10.0,
):
    """
    Assert that actual timestamp exists and is within tolerance_seconds of expected timestamp,
    or simply verify non-null existence if expected is True.
    """
    if expected is True:
        assert actual is not None, "Expected timestamp to be present, but got None"
        return
    if expected is False or expected is None:
        assert actual is None, f"Expected timestamp to be None, but got '{actual}'"
        return

    assert actual is not None, f"Expected timestamp near {expected}, but got None"
    dt_actual = parse_datetime(actual)
    dt_expected = parse_datetime(expected)
    diff = abs((dt_actual - dt_expected).total_seconds())
    assert diff <= tolerance_seconds, (
        f"Timestamp mismatch: actual {dt_actual} differs from expected {dt_expected} "
        f"by {diff:.2f}s (tolerance: {tolerance_seconds}s)"
    )


class ApexFlowAssert:
    """
    Industry-standard assertion helper for ApexFlow entities.
    Validates field-level completeness with timestamp delta tolerance.
    """

    TIMESTAMP_FIELDS = {"created_at", "started_at", "completed_at", "locked_until", "last_heartbeat"}

    @classmethod
    def assert_workflow_run(cls, run_data: Dict[str, Any], **expected_fields):
        """
        Assert WorkflowRun fields. Only provided expected_fields are validated.
        """
        assert isinstance(run_data, dict), f"Expected dict for WorkflowRun data, got {type(run_data)}"
        assert "id" in run_data, "WorkflowRun missing required 'id' field"
        assert "status" in run_data, "WorkflowRun missing required 'status' field"

        for field, expected_val in expected_fields.items():
            actual_val = run_data.get(field)
            if field in cls.TIMESTAMP_FIELDS and expected_val is not None:
                assert_timestamp_within_range(actual_val, expected_val)
            else:
                assert actual_val == expected_val, (
                    f"WorkflowRun.{field} mismatch: expected {expected_val!r}, got {actual_val!r} "
                    f"(Full object: {run_data})"
                )

    @classmethod
    def assert_step(cls, step_data: Dict[str, Any], **expected_fields):
        """
        Assert WorkflowStep fields. Only provided expected_fields are validated.
        """
        assert isinstance(step_data, dict), f"Expected dict for WorkflowStep data, got {type(step_data)}"
        assert "id" in step_data, "WorkflowStep missing required 'id' field"
        assert "step_name" in step_data, "WorkflowStep missing required 'step_name' field"
        assert "status" in step_data, "WorkflowStep missing required 'status' field"

        for field, expected_val in expected_fields.items():
            actual_val = step_data.get(field)
            if field in cls.TIMESTAMP_FIELDS and expected_val is not None:
                assert_timestamp_within_range(actual_val, expected_val)
            else:
                assert actual_val == expected_val, (
                    f"WorkflowStep.{field} mismatch: expected {expected_val!r}, got {actual_val!r} "
                    f"(Full object: {step_data})"
                )

    @classmethod
    def assert_ref_descriptor(
        cls,
        ref: Dict[str, Any],
        min_size: Optional[int] = None,
        expected_content_type: Optional[str] = None,
    ):
        """
        Assert an offloaded $apexflow_ref descriptor payload structure.
        """
        assert isinstance(ref, dict), f"Expected dict for $apexflow_ref, got {type(ref)}"
        assert ref.get("$apexflow_ref") is True, f"Missing '$apexflow_ref: true' in descriptor: {ref}"
        assert "key" in ref and ref["key"], f"Missing 'key' in $apexflow_ref descriptor: {ref}"
        assert "size_bytes" in ref and isinstance(ref["size_bytes"], int), f"Invalid 'size_bytes' in ref: {ref}"

        if min_size is not None:
            assert ref["size_bytes"] >= min_size, (
                f"$apexflow_ref size {ref['size_bytes']} bytes is smaller than expected minimum {min_size} bytes"
            )

        if expected_content_type is not None:
            assert expected_content_type in ref.get("content_type", ""), (
                f"$apexflow_ref content_type mismatch: expected {expected_content_type}, got {ref.get('content_type')}"
            )
