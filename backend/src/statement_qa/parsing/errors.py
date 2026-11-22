"""Errors raised while parsing a statement."""


class StatementParseError(ValueError):
    """The input isn't a statement we can read, or a row on it doesn't parse."""
