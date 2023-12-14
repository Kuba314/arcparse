from abc import ABC, abstractmethod
from argparse import _ActionsContainer
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, overload

from ._typehints import (
    extract_collection_type,
    extract_optional_type,
    extract_type_from_typehint,
)
from .converters import itemwise


class Void:
    pass

void = Void()


@dataclass(kw_only=True, eq=False)
class MxGroup:
    required: bool = False


@dataclass(kw_only=True)
class _BaseArgument(ABC):
    mx_group: MxGroup | None = None
    help: str | None = None

    def apply(self, actions_container: _ActionsContainer, name: str, typehint: type) -> None:
        args = self.get_argparse_args(name, typehint)
        kwargs = self.get_argparse_kwargs(name, typehint)
        actions_container.add_argument(*args, **kwargs)

    @abstractmethod
    def get_argparse_args(self, name: str, typehint: type) -> list[str]:
        ...

    def get_argparse_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = {}
        if self.help is not None:
            kwargs["help"] = self.help
        return kwargs


@dataclass(kw_only=True)
class _BaseValueArgument[T](_BaseArgument):
    default: T | Void = void
    choices: list[T] | None = None
    converter: Callable[[str], T] | None = None
    name_override: str | None = None
    at_least_one: bool = False

    def need_multiple(self, typehint: type) -> bool:
        return (
            (self.converter is None and extract_collection_type(typehint) is not None)
            or isinstance(self.converter, itemwise)
        )

    def get_argparse_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name, typehint)

        if self.converter is None:
            type_ = extract_type_from_typehint(typehint)
            if type_ is not str:
                if extract_collection_type(typehint):
                    self.converter = itemwise(type_)  # type: ignore (list[T@itemwise] somehow incompatible with T@_BaseValueArgument)
                else:
                    self.converter = type_

        if self.converter is not None:
            kwargs["type"] = self.converter
        if self.default is not void:
            kwargs["default"] = self.default
        if self.choices is not None:
            kwargs["choices"] = self.choices

        if self.need_multiple(typehint) and not self.at_least_one and self.default is void:
            kwargs["default"] = []

        return kwargs


@dataclass
class _Positional[T](_BaseValueArgument[T]):
    def get_argparse_args(self, name: str, typehint: type) -> list[str]:
        return [name]

    def get_argparse_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name, typehint)

        type_is_optional = bool(extract_optional_type(typehint))
        type_is_collection = bool(extract_collection_type(typehint))
        optional = type_is_optional or type_is_collection or self.default is not void

        if self.name_override is not None:
            kwargs["metavar"] = self.name_override

        if self.need_multiple(typehint):
            kwargs["nargs"] = "+" if self.at_least_one else "*"
            kwargs["metavar"] = self.name_override if self.name_override is not None else name.upper()
        elif optional:
            kwargs["nargs"] = "?"
        return kwargs


@dataclass
class _Option[T](_BaseValueArgument[T]):
    short: str | None = None
    short_only: bool = False
    append: bool = False

    def get_argparse_args(self, name: str, typehint: type) -> list[str]:
        name = self.name_override if self.name_override is not None else name.replace("_", "-")
        args = [f"--{name}"]
        if self.short_only:
            assert self.short is not None
            return [self.short]
        elif self.short is not None:
            args.insert(0, self.short)

        return args

    def get_argparse_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name, typehint)
        if self.need_multiple(typehint):
            if self.append:
                kwargs["action"] = "append"
            else:
                kwargs["nargs"] = "+" if self.at_least_one else "*"

        if self.name_override is not None:
            kwargs["dest"] = name
            kwargs["metavar"] = self.name_override.replace("-", "_").upper()
        elif self.short_only:
            kwargs["dest"] = name

        type_is_optional = bool(extract_optional_type(typehint))
        type_is_collection = bool(extract_collection_type(typehint))
        required = (not (type_is_optional or type_is_collection) and self.default is void) or self.at_least_one
        if required:
            kwargs["required"] = True

        return kwargs


@dataclass
class _Flag(_BaseArgument):
    short: str | None = None
    short_only: bool = False

    def get_argparse_args(self, name: str, typehint: type) -> list[str]:
        args = [f"--{name.replace("_", "-")}"]
        if self.short_only:
            assert self.short is not None
            return [self.short]
        elif self.short is not None:
            args.insert(0, self.short)

        return args

    def get_argparse_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name, typehint)
        kwargs["action"] = "store_true"

        if self.short_only:
            kwargs["dest"] = name
        return kwargs


@dataclass
class _NoFlag(_BaseArgument):
    def get_argparse_args(self, name: str, typehint: type) -> list[str]:
        return [f"--no-{name.replace("_", "-")}"]

    def get_argparse_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name, typehint)
        kwargs["action"] = "store_false"

        kwargs["dest"] = name
        return kwargs


@overload
def positional[T](
    *,
    default: T | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    at_least_one: Literal[False] = False,
    mx_group: MxGroup | None = None,
    help: str | None = None,
) -> T: ...

@overload
def positional[T](
    *,
    default: list[T] | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], list[T]] | None = None,
    name_override: str | None = None,
    at_least_one: Literal[True] = True,
    mx_group: MxGroup | None = None,
    help: str | None = None,
) -> list[T]: ...

def positional(  # type: ignore
    *,
    default=void,
    choices=None,
    converter=None,
    name_override=None,
    at_least_one=False,
    mx_group=None,
    help=None,
):
    return _Positional(
        default=default,
        choices=choices,
        converter=converter,
        name_override=name_override,
        at_least_one=at_least_one,
        mx_group=mx_group,
        help=help,
    )


@overload
def option[T](
    short: str | None = None,
    *,
    short_only: bool = False,
    default: T | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    append: Literal[False] = False,
    at_least_one: Literal[False] = False,
    mx_group: MxGroup | None = None,
    help: str | None = None,
) -> T: ...


@overload
def option[T](
    short: str | None = None,
    *,
    short_only: bool = False,
    default: list[T] | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], list[T]] | None = None,
    name_override: str | None = None,
    append: Literal[True] = True,
    at_least_one: Literal[False] = False,
    mx_group: MxGroup | None = None,
    help: str | None = None,
) -> list[T]: ...

@overload
def option[T](
    short: str | None = None,
    *,
    short_only: bool = False,
    default: list[T] | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], list[T]] | None = None,
    name_override: str | None = None,
    append: Literal[False] = False,
    at_least_one: Literal[True] = True,
    mx_group: MxGroup | None = None,
    help: str | None = None,
) -> list[T]: ...

def option(  # type: ignore
    short=None,
    *,
    short_only=False,
    default=void,
    choices=None,
    converter=None,
    name_override=None,
    append=False,
    at_least_one=False,
    mx_group=None,
    help=None,
):
    if short_only and short is None:
        raise Exception("`short_only` cannot be True if `short` is not provided")
    return _Option(
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
    )


def flag(
    short: str | None = None,
    *,
    short_only: bool = False,
    mx_group: MxGroup | None = None,
    help: str | None = None,
) -> bool:
    if short_only and short is None:
        raise Exception("`short_only` cannot be True if `short` is not provided")
    return _Flag(
        short=short,
        short_only=short_only,
        help=help,
        mx_group=mx_group,
    )  # type: ignore


def no_flag(*, mx_group: MxGroup | None = None, help: str | None = None) -> bool:
    return _NoFlag(mx_group=mx_group, help=help)  # type: ignore
