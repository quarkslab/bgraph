class BGraphException(Exception):
    """Main exception of the application."""

    pass


class BGraphManifestException(BGraphException):
    """Manifest exceptions."""

    pass


class BGraphBuilderException(BGraphException):
    """Builder exception"""

    pass


class BGraphParserException(BGraphBuilderException):
    """Parsers exceptions"""

    pass


class BGraphLoadingException(BGraphException):
    """Loading exceptions"""

    pass


class BGraphMissingSectionException(BGraphParserException):
    """Missing sections exception"""

    pass


class BGraphViewerException(BGraphException):
    """Viewever exception"""

    pass


class BGraphNodeNotFound(BGraphViewerException):
    """Missing node exceptions"""

    pass


class BGraphTooManyNodes(BGraphViewerException):
    """Too many nodes exceptions"""

    pass
