from collections.abc import Callable
from typing import Any

from ._arguments import Void, void
from ._partial_arguments import (
    BasePartialArgument,
    BasePartialValueArgument,
    PartialFlag,
    PartialMxGroup,
    PartialNoFlag,
    PartialOption,
    PartialPositional,
    PartialSubparsers,
    PartialTriFlag,
)


def positional[T](
    *,
    default: T | str | Void = void,
    choices: list[str] | None = None,
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
    choices: list[str] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    append: bool = False,
    at_least_one: bool = False,
    mx_group: PartialMxGroup | None = None,
    help: str | None = None,
) -> T:
    if short_only and short is None:
        raise ValueError("`short_only` cannot be True if `short` is not provided")

    if append and at_least_one:
        raise ValueError("`append` is incompatible with `at_least_one`")

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
    if short_only and short is None:
        raise ValueError("`short_only` cannot be True if `short` is not provided")
    return PartialFlag(
        short=short,
        short_only=short_only,
        help=help,
        mx_group=mx_group,
    )  # type: ignore


def no_flag(*, mx_group: PartialMxGroup | None = None, help: str | None = None) -> bool:
    return PartialNoFlag(mx_group=mx_group, help=help)  # type: ignore


def tri_flag(mx_group: PartialMxGroup | None = None) -> bool | None:
    return PartialTriFlag(mx_group=mx_group)  # type: ignore


def mx_group(*, required: bool = False) -> PartialMxGroup:
    return PartialMxGroup(required=required)


def subparsers(*args: str) -> Any:
    return PartialSubparsers(names=list(args))
