"""Hierarchy of errors of the import/export application."""


class ApplicationError(Exception):
    """Base class for all errors of the import/export application."""


class ConfigurationError(ApplicationError):
    """The configuration file is missing or invalid."""


class DataError(ApplicationError):
    """Base class for errors in input or output data."""


class DataImportError(DataError):
    """Input data cannot be read."""


class RecordValidationError(DataError):
    """One input record does not satisfy the validation rules."""

    def __init__(self, message: str, *, line_number: int, field: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field

    def __str__(self) -> str:
        where = f"рядок {self.line_number}" + (f", поле {self.field}" if self.field else "")
        return f"{where}: {super().__str__()}"


class DataExportError(DataError):
    """Output data cannot be written."""
