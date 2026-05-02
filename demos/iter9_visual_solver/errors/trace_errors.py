"""Solver event trace loading errors."""


class DemoTraceError(Exception):
    """Base class for event trace failures."""


class DemoTraceJsonError(DemoTraceError):
    """Raised when a JSONL trace row is malformed."""


class DemoTraceValidationError(DemoTraceError):
    """Raised when a trace row violates the event contract."""

