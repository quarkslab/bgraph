import functools
import logging
import pathlib

from bgraph.types import Dict, List, Any, Generator, Tuple, Callable, Union


def recurse(mapping: Dict[Any, Any]) -> Generator[Tuple[Any, Any], None, None]:
    """Recurse through a mapping and yield every key value pairs.

    :param mapping: A mapping to unroll
    """
    for key, value in mapping.items():
        if type(value) is dict:
            yield from recurse(value)
        else:
            yield key, value


def create_logger(logger_name: str) -> logging.Logger:
    """Set up logging using the `logger_name`"""

    logger = logging.getLogger(logger_name)

    # Create console handler if not already present
    if not logger.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


def no_except(f: Callable) -> Callable:
    """Prevent failures when running f."""

    logger: logging.Logger = create_logger(__name__)

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception(e)

    return wrapper


def clean_mirror_path(mirror: str) -> Union[str, pathlib.Path]:
    """Convert the user input from command line to an acceptable format for the app.

    Note: If the user provided an URL, it will remove any trailing '/'.

    :param mirror: User input
    :return: Either a Path object or a string
    """
    # First, detect if the string is an url
    mirror_path: Union[str, pathlib.Path] = (
        pathlib.Path(mirror) if "http" not in mirror else mirror
    )

    # Remove trailing '/' if needed
    if isinstance(mirror_path, str) and mirror_path.endswith("/"):
        mirror_path = mirror_path[:-1]

    return mirror_path
