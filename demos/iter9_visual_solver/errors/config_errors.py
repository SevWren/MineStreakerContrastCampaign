"""Config loading and validation errors."""


class DemoConfigError(Exception):
    """Base class for demo config failures."""


class DemoConfigFileNotFoundError(DemoConfigError):
    """Raised when a config file does not exist."""


class DemoConfigJsonError(DemoConfigError):
    """Raised when a config file is not valid JSON."""


class DemoConfigValidationError(DemoConfigError):
    """Raised when config data violates the Pydantic contract."""

