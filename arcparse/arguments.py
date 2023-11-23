from abc import ABC, abstractmethod
from argparse import ArgumentParser
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

from .converters import itemwise
from .typehints import extract_collection_type, extract_optional_type, extract_type_from_typehint

class Void:
    pass

void = Void()


@dataclass(kw_only=True)
class _BaseArgument(ABC):
    help: str | None = None
    typehint: type = field(init=False, default=Void)

    def apply(self, parser: ArgumentParser, name: str) -> None:
        # value is overriden, do not add argument
        if isinstance(self, _ValueOverride) and self.value_override is not void:
            return

        args = self.get_argparse_args(name)
        kwargs = self.get_argparse_kwargs(name)
        parser.add_argument(*args, **kwargs)

    @abstractmethod
    def get_argparse_args(self, name: str) -> list[str]:
        ...

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = {}
        if self.help is not None:
            kwargs["help"] = self.help
        return kwargs

    def resolve_with_typehint(self, typehint: type) -> None:
        self.typehint = typehint


@dataclass(kw_only=True)
class _BaseValueArgument[T](_BaseArgument):
    default: T | Void = void
    choices: list[T] | None = None
    converter: Callable[[str], T] | None = None
    name_override: str | None = None
    multiple: bool = False
    type_requires_value: bool = False

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        if self.converter is not None:
            kwargs["type"] = self.converter
        if self.default is not void:
            kwargs["default"] = self.default
        if self.choices is not None:
            kwargs["choices"] = self.choices
        if self.multiple:
            if self.default is void:
                kwargs["default"] = []

        return kwargs

    def resolve_with_typehint(self, typehint: type) -> None:
        super().resolve_with_typehint(typehint)

        # assume multiple arguments if no converter set and expected type is a collection
        if (
            (self.converter is None and extract_collection_type(typehint))
            or (isinstance(self.converter, itemwise))
        ):
            self.multiple = True

        if self.converter is None:
            type_ = extract_type_from_typehint(typehint)
            if type_ is bool:
                raise Exception("Argument yielding a value can't be typed as `bool`")

            if type_ is not str:
                self.converter = type_


@dataclass
class _Positional[T](_BaseValueArgument[T]):
    def get_argparse_args(self, name: str) -> list[str]:
        if self.name_override is not None:
            return [self.name_override]
        return [name]

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        if self.multiple:
            kwargs["nargs"] = "*"
            kwargs["metavar"] = name.upper()
        elif not self.type_requires_value or self.default is not void:
            kwargs["nargs"] = "?"
        return kwargs

    def resolve_with_typehint(self, typehint: type) -> None:
        super().resolve_with_typehint(typehint)
        is_optional = bool(extract_optional_type(typehint))
        is_collection = bool(extract_collection_type(typehint))
        if is_optional or is_collection:
            self.type_requires_value = False


@dataclass
class _Option[T](_BaseValueArgument[T]):
    short: str | None = None
    short_only: bool = False
    append: bool = False

    def get_argparse_args(self, name: str) -> list[str]:
        name = self.name_override if self.name_override is not None else name.replace("_", "-")
        args = [f"--{name}"]
        if self.short_only:
            assert self.short is not None
            return [self.short]
        elif self.short is not None:
            args.insert(0, self.short)

        return args

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        if self.multiple:
            if self.append:
                kwargs["action"] = "append"
            else:
                kwargs["nargs"] = "*"

        if self.name_override is not None:
            kwargs["dest"] = name
            kwargs["metavar"] = self.name_override.replace("-", "_").upper()
        elif self.short_only:
            kwargs["dest"] = name

        if self.type_requires_value and self.default is void:
            kwargs["required"] = True

        return kwargs

    def resolve_with_typehint(self, typehint: type) -> None:
        super().resolve_with_typehint(typehint)
        is_optional = bool(extract_optional_type(typehint))
        is_collection = bool(extract_collection_type(typehint))
        if not is_optional and not is_collection:
            self.type_requires_value = True


@dataclass(kw_only=True)
class _ValueOverride[T]:
    """Value override for arguments

    Utilized in flags and no_flags when providing dynamic defaults for them.
    Setting a non-void `value_override` causes the argument to not be included
    into ArgumentParser and the value will be always contained in the return
    arguments.
    """
    value_override: T | Void = void


@dataclass
class _Flag(_ValueOverride[bool], _BaseArgument):
    short: str | None = None
    short_only: bool = False

    def get_argparse_args(self, name: str) -> list[str]:
        args = [f"--{name.replace("_", "-")}"]
        if self.short_only:
            assert self.short is not None
            return [self.short]
        elif self.short is not None:
            args.insert(0, self.short)

        return args

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        kwargs["action"] = "store_true"

        if self.short_only:
            kwargs["dest"] = name
        return kwargs


@dataclass
class _NoFlag(_ValueOverride[bool], _BaseArgument):
    def get_argparse_args(self, name: str) -> list[str]:
        return [f"--no-{name.replace("_", "-")}"]

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        kwargs["action"] = "store_false"

        kwargs["dest"] = name
        return kwargs


def positional[T](
    *,
    default: T | Void = void,
    choices: list[T] | None = None,
    converter: Callable[[str], T] | None = None,
    name_override: str | None = None,
    help: str | None = None,
) -> T:
    return _Positional(
        default=default,
        choices=choices,
        converter=converter,
        name_override=name_override,
        type_requires_value=True,
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
    help: str | None = None,
) -> T:
    if short_only and short is None:
        raise Exception("`short_only` cannot be True if `short` is not provided")
    return _Option(
        short=short,
        short_only=short_only,
        default=default,
        choices=choices,
        converter=converter,
        name_override=name_override,
        type_requires_value=False,
        append=append,
        help=help,
    )  # type: ignore


def flag(
    short: str | None = None,
    *,
    short_only: bool = False,
    help: str | None = None,
) -> bool:
    if short_only and short is None:
        raise Exception("`short_only` cannot be True if `short` is not provided")
    return _Flag(
        short=short,
        short_only=short_only,
        help=help,
    )  # type: ignore


def no_flag(*, help: str | None = None) -> bool:
    return _NoFlag(help=help)  # type: ignore
