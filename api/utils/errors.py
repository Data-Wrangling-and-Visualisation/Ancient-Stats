from typing import Generic, TypeVar, Union, Optional, Callable, Any, Tuple
from functools import wraps

import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")
E = TypeVar("E", bound=Any)


class Ok(Generic[T]):
    __slots__ = ("value", "is_error")

    def __init__(self, value: T):
        self.value = value
        self.is_error = False

    def __iter__(self):
        yield self.value
        yield self.is_error


# Ideal case: create error-type by the error that actually could happen
class Err(Generic[E]):
    __slots__ = ("value", "is_error")

    def __init__(self):
        self.value = None
        self.is_error = True

    def __iter__(self):
        yield None
        yield self.is_error


Result = Union[Ok[T], Err[E]]


# TODO: Check the behavior with async functions
def error_handler(
    func: Callable[..., Result[T, E]],
) -> Callable[..., Tuple[Optional[T], Optional[E]]]:
    @wraps(func)
    def wrapper(*args, **kwargs) -> Tuple[Optional[T], Optional[E]]:
        try:
            result = func(*args, **kwargs)
        except:
            # general error if the error was thrown by 3d-side function/library
            print(f"General exception by {func.__name__=} in error_handeler")
            return Err()
        return result

    return wrapper


class ErrPlayerIdNotFound(Err):
    __slots__ = ("value", "is_error")

    def __init__(self):
        self.value = None
        self.is_error = True

        logger.error("PlayerIdNotFound was triggered")

    def __iter__(self):
        yield None
        yield self.is_error


class ErrDataLoadingFailed(Err):
    __slots__ = ("value", "is_error")

    def __init__(self, msg: str = "default msg of ErrDataLoadingFailed"):
        self.value = None
        self.is_error = True

        logger.error(f"Erorr logs: {msg}")

    def __iter__(self):
        yield None
        yield self.is_error


class ErrHttpxRequest(Err):
    __slots__ = ("value", "is_error")

    def __init__(self, msg: str = "default msg of ErrDataLoadingFailed"):
        self.value = None
        self.is_error = True

        logger.error(f"Erorr logs: {msg}")

    def __iter__(self):
        yield None
        yield self.is_error


class ErrInternal(Err):
    __slots__ = ("value", "is_error")

    def __init__(self, msg: str = "default msg of ErrDataLoadingFailed"):
        self.value = None
        self.is_error = True

        logger.error(f"Erorr logs: {msg}")

    def __iter__(self):
        yield None
        yield self.is_error
