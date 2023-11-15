from abc import ABC, abstractmethod
from argparse import ArgumentParser
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

class Void:
    pass

void = Void()


@dataclass(kw_only=True)
class _BaseArgument(ABC):
    help: str | None = None

    def apply(self, parser: ArgumentParser, name: str) -> None:
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


@dataclass(kw_only=True)
class _BaseValueArgument[T](_BaseArgument):
    default: T | Void = void
    choices: list[T] | None = None
    converter: Callable[[str], T] | None = None
    name_override: str | None = None
    multiple: bool = False
    required: bool = False

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
        elif not self.required:
            kwargs["nargs"] = "?"
        return kwargs


@dataclass
class _Option[T](_BaseValueArgument[T]):
    short: str | None = None
    short_only: bool = False

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
            kwargs["action"] = "append"

        if self.name_override is not None:
            kwargs["dest"] = name
            kwargs["metavar"] = self.name_override.replace("-", "_").upper()
        elif self.short_only:
            kwargs["dest"] = name

        if self.required:
            kwargs["required"] = True

        return kwargs


@dataclass
class _Flag(_BaseArgument):
    short: str | None = None
    short_only: bool = False
    default: bool = False

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
        kwargs["action"] = "store_false" if self.default else "store_true"

        if self.short_only:
            kwargs["dest"] = name
        return kwargs


@dataclass
class _NoFlag(_BaseArgument):
    def get_argparse_args(self, name: str) -> list[str]:
        return [f"--no-{name.replace("_", "-")}"]

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        kwargs["action"] = "store_false"

        kwargs["dest"] = name
        return kwargs


def positional[T](
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
        required=True,
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
        required=False,
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
