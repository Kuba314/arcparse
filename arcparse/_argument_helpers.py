from collections.abc import Callable
from typing import Any

from ._arguments import Void, void
from ._partial_arguments import (
    _PartialFlag,
    _PartialMxGroup,
    _PartialNoFlag,
    _PartialOption,
    _PartialPositional,
    _PartialSubparsers,
)


def positional[T](
    *,
    default: T | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    at_least_one: bool = False,
    mx_group: _PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    return _PartialPositional(
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
    default: T | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    append: bool = False,
    at_least_one: bool = False,
    mx_group: _PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    if short_only and short is None:
        raise ValueError("`short_only` cannot be True if `short` is not provided")

    if append and at_least_one:
        raise ValueError("`append` is incompatible with `at_least_one`")

    return _PartialOption(
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
    mx_group: _PartialMxGroup | None = None,
    help: str | None = None,
) -> bool:
    if short_only and short is None:
        raise ValueError("`short_only` cannot be True if `short` is not provided")
    return _PartialFlag(
        short=short,
        short_only=short_only,
        help=help,
        mx_group=mx_group,
    )  # type: ignore


def no_flag(*, mx_group: _PartialMxGroup | None = None, help: str | None = None) -> bool:
    return _PartialNoFlag(mx_group=mx_group, help=help)  # type: ignore


def mx_group(*, required: bool = False) -> _PartialMxGroup:
    return _PartialMxGroup(required=required)


def subparsers(*args: str) -> Any:
    return _PartialSubparsers(names=list(args))
