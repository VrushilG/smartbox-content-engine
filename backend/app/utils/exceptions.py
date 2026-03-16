class SmartboxBaseError(Exception):
    """Base class for all Smartbox Content Engine exceptions."""


class CSVValidationError(SmartboxBaseError):
    """Raised when an uploaded CSV file fails validation.

    Covers: empty file, missing columns, invalid category values,
    unparseable rows, or any other data integrity issue.
    """


class LLMError(SmartboxBaseError):
    """Raised when an LLM service call fails.

    Covers: API errors, timeout, non-JSON response, or model-level refusal.
    """


class PipelineError(SmartboxBaseError):
    """Raised for orchestration-level failures in core/pipeline.py.

    Covers: unexpected state, missing service configuration, or any
    error that is not specific to CSV parsing or a single LLM call.
    """
