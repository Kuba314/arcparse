from collections.abc import Callable, Collection
from typing import Any, overload
import re

from arcparse.errors import InvalidArgument

from ._partial_arguments import (
    PartialFlag,
    PartialMxGroup,
    PartialOption,
    PartialPositional,
    PartialSubparsers,
    PartialTriFlag,
)
from .arguments import Void, void


def _check_short_format(short: str) -> None:
    if not re.match(r"^-[^-]+$", short):
        raise InvalidArgument(f'Invalid argument short-hand "{short}", expected a dash followed by non-dash characters')


def positional[T](
    *,
    default: T | str | Void = void,
    choices: Collection[str] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    at_least_one: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    """
    Create a positional argument. `value` is the argument value in the following snippet:
    ```
    python3 program.py value
    ```

    :param T | str default: Value used if no argument value was provided. If the value is not the desired type, it will be converted with `converter`.
    :param Collection[str] choices: Valid argument values
    :param Callable[[str], T] converter: Callable to convert string argument value to desired type.
    :param str name_override: Name override to use for passing values to this argument.
    :param bool at_least_one: Require at least one value when allowing multiple values.
    :param PartialMxGroup mx_group: Mutually exclusive group to assign argument into.
    :param str help: Description of the argument.
    """
    return PartialPositional(
        default=default,
        choices=choices,
        converter=converter,
        name_override=name_override,
        at_least_one=at_least_one,
        mx_group=mx_group,
        help=help,
    )  # type: ignore


# Note: default is replaced by arguments when `append` is used.
def option[T](
    short: str | None = None,
    *,
    short_only: bool = False,
    default: T | str | Void = void,
    choices: Collection[str] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    append: bool = False,
    at_least_one: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    """
    Create an option argument. `value` is the argument value in the following snippet:
    ```
    python3 program.py --arg value
    ```

    :param str | None short: Allow short-hand form alongside longer form.
    :param bool short_only: Only use short-hand form.
    :param T | str default: Value used if no argument value was provided. If the value is not the desired type, it will be converted with `converter`.
    :param Collection[str] choices: Valid argument values
    :param Callable[[str], T] converter: Callable to convert string argument value to desired type.
    :param str name_override: Name override to use for passing values to this argument.
    :param bool append: Use append argparse action when allowing multiple values.
    :param bool at_least_one: Require at least one value when allowing multiple values.
    :param PartialMxGroup mx_group: Mutually exclusive group to assign argument into.
    :param str help: Description of the argument.
    """
    if short is not None:
        _check_short_format(short)

    if short_only and name_override is not None:
        raise InvalidArgument("`short_only` cannot be True if `name_override` is provided")

    return PartialOption(
        short=short,
        short_only=short_only,
        default=default,
        choices=choices,
        converter=converter,
        name_override=name_override,
        append=append,
        at_least_one=at_least_one,
        mx_group=mx_group,
        help=help,
    )  # type: ignore


def flag(
    short: str | None = None,
    *,
    short_only: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> bool:
    """
    Create a flag. The flag is enabled in the following snippet:
    ```
    python3 program.py --flag
    ```

    :param str | None short: Allow short-hand form alongside longer form.
    :param bool short_only: Only use short-hand form.
    :param PartialMxGroup mx_group: Mutually exclusive group to assign argument into.
    :param str help: Description of the argument.
    """
    if short is not None:
        _check_short_format(short)

    return PartialFlag(
        short=short,
        short_only=short_only,
        help=help,
        mx_group=mx_group,
    )  # type: ignore


def no_flag(
    short: str | None = None,
    *,
    short_only: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> bool:
    """
    Create a no-flag. This works in the exact opposite way to `flag()`. Passing the no-flag disables the flag. The `no-` prefix is used automatically.
    ```
    python3 program.py --no-flag
    ```

    :param str | None short: Allow short-hand form alongside longer form.
    :param bool short_only: Only use short-hand form.
    :param PartialMxGroup mx_group: Mutually exclusive group to assign argument into.
    :param str help: Description of the argument.
    """
    if short is not None:
        _check_short_format(short)

    return PartialFlag(
        short=short,
        short_only=short_only,
        no_flag=True,
        help=help,
        mx_group=mx_group,
    )  # type: ignore


def tri_flag(mx_group: PartialMxGroup | None = None) -> bool | None:
    """
    Create a tri-flag. This creates both the `flag()` and `no_flag()` arguments in a mutually exclusive group.
    ```
    python3 program.py            # value is None
    python3 program.py --flag     # value is True
    python3 program.py --no-flag  # value is False
    ```

    :param str help: Description of the argument.
    """
    return PartialTriFlag(mx_group=mx_group)  # type: ignore


def mx_group(*, required: bool = False) -> PartialMxGroup:
    """
    Create a mutually exclusive group.

    :param bool required: Require a single argument to be passed.
    """
    return PartialMxGroup(required=required)


@overload
def subparsers(*args: str) -> Any:
    """
    Create subparsers. Assign to a union of subparser shapes.

    Example usage:
    ```
    class Args:
        action: AddAction | DeleteAction = subparsers("add", "delete")
    ```

    :param str *args: Names to be used for the subparsers. Has to have the same length as the assigned-to subparser shapes union.
    """
    ...


@overload
def subparsers[T](**kwargs: type[T]) -> T:
    """
    Create subparsers.

    Example usage:
    ```
    class Args:
        action: Action = subparsers(add=AddAction, delete=DeleteAction)
    ```

    :param type[T] **kwargs: Subparser shapes assigned to names used for the subparsers.
    """
    ...


def subparsers(*args, **kwargs) -> Any:
    if args:
        assert all(isinstance(arg, str) for arg in args)
        return PartialSubparsers(names=list(args))
    elif kwargs:
        assert all(isinstance(value, type) for value in kwargs.values())
        return PartialSubparsers(names=list(kwargs.keys()), shapes=list(kwargs.values()))


def dict_positional[T](
    dict_: dict[str, T],
    *,
    default: T | Void = void,
    name_override: str | None = None,
    at_least_one: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    """Creates positional() from dict by pre-filling choices and converter"""

    if default is not void and default not in dict_.values():
        raise InvalidArgument("dict_positional default must be a value in dict")

    return positional(
        default=default,
        choices=list(dict_.keys()),
        converter=dict_.__getitem__,
        name_override=name_override,
        at_least_one=at_least_one,
        mx_group=mx_group,
        help=help,
    )


def dict_option[T](
    dict_: dict[str, T],
    *,
    short: str | None = None,
    short_only: bool = False,
    default: T | Void = void,
    name_override: str | None = None,
    append: bool = False,
    at_least_one: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    """Creates option() from dict by pre-filling choices and converter"""

    if default is not void and default not in dict_.values():
        raise InvalidArgument("dict_positional default must be a value in dict")

    return option(
        short=short,
        short_only=short_only,
        default=default,
        choices=list(dict_.keys()),
        converter=dict_.__getitem__,
        name_override=name_override,
        append=append,
        at_least_one=at_least_one,
        mx_group=mx_group,
        help=help,
    )
