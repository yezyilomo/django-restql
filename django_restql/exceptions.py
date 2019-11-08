class DjangoRESTQLException(Exception):
    """Base class for exceptions in this module."""


class InvalidOperation(DjangoRESTQLException):
    """Invalid Operation Exception."""


class FieldNotFound(DjangoRESTQLException):
    """Field Not Found Exception."""