from collections.abc import Collection
from typing import Any

from ._validations import Constraint, ImplyConstraint, RequireConstraint


__all__ = [
    "Constraint",
    "ImplyConstraint",
    "RequireConstraint",
    "imply",
    "require",
]


def imply(arg: Any, required: Collection[Any] = (), disallowed: Collection[Any] = ()) -> ImplyConstraint:
    """
    Require and disallow arguments when arg is passed.

    If `arg` is present and the constraint is fulfilled, no subsequent constraints are checked.

    :param Any arg: argument to check existence for
    :param Collection[Any] required: required arguments when arg is passed
    :param Collection[Any] disallowed: disallowed arguments when arg is passed
    """
    return ImplyConstraint(arg, required=required, disallowed=disallowed)


def require(*args: Any) -> RequireConstraint:
    """
    Require arguments to be present.
    """
    return RequireConstraint(args)
