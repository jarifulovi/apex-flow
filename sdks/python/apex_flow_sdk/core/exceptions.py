class ApexFlowSDKError(Exception):
    """Base exception for ApexFlow SDK errors."""

    pass


class StepFailedError(ApexFlowSDKError):
    """Raised when a workflow step fails after exhausting retries."""

    def __init__(self, step_name: str, message: str, original_error: Exception = None):
        super().__init__(f"Step '{step_name}' failed: {message}")
        self.step_name = step_name
        self.message = message
        self.original_error = original_error


class NonRetryableError(ApexFlowSDKError):
    """Raised when an error should fail immediately without retrying."""

    pass
