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
        raise InvalidArgument(f"Invalid argument short-hand \"{short}\", expected a dash followed by non-dash characters")


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
    return PartialPositional(
        default=default,
        choices=choices,
        converter=converter,
        name_override=name_override,
        at_least_one=at_least_one,
        mx_group=mx_group,
        help=help,
    )  # type: ignore


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
    if short is not None:
        _check_short_format(short)

    if short_only and name_override is not None:
        raise InvalidArgument("`short_only` cannot be True if `name_override` is provided")

    if append and at_least_one:
        raise InvalidArgument("`append` is incompatible with `at_least_one`")

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
    return PartialTriFlag(mx_group=mx_group)  # type: ignore


def mx_group(*, required: bool = False) -> PartialMxGroup:
    return PartialMxGroup(required=required)


@overload
def subparsers(*args: str) -> Any:
    ...

@overload
def subparsers[T](**kwargs: type[T]) -> T:
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
