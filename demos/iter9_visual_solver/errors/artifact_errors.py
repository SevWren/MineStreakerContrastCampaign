"""Artifact loading errors."""


class DemoArtifactError(Exception):
    """Base class for demo artifact failures."""


class DemoArtifactNotFoundError(DemoArtifactError):
    """Raised when a required artifact is missing."""


class DemoArtifactValidationError(DemoArtifactError):
    """Raised when an artifact has invalid content."""

