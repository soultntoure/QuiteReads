"""Custom application exceptions."""


class DataLoadError(Exception):
    """Raised when dataset loading fails."""

    pass


class DataPreprocessError(Exception):
    """Raised when data preprocessing fails."""

    pass


class TrainingError(Exception):
    """Raised when model training fails."""

    pass


class ConfigurationError(Exception):
    """Raised when experiment configuration is invalid."""

    pass


class FederatedSimulationError(Exception):
    """Raised when FL simulation fails."""

    pass
