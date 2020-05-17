class DjangoRESTQLException(Exception):
    """Base class for exceptions in this package."""


class InvalidOperation(DjangoRESTQLException):
    """Invalid Operation Exception."""


class FieldNotFound(DjangoRESTQLException):
    """Field Not Found Exception."""


class QueryFormatError(DjangoRESTQLException):
    """Invalid Query Format."""
