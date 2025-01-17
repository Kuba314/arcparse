from abc import ABC, abstractmethod
from argparse import _ActionsContainer, _MutuallyExclusiveGroup
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol


if TYPE_CHECKING:
    from .parser import Parser


__all__ = [
    "ContainerApplicable",
    "BaseArgument",
    "Flag",
    "TriFlag",
    "BaseValueArgument",
    "Positional",
    "Option",
    "MxGroup",
    "Subparsers",
    "void",
]


class Void:
    pass


void = Void()


class ContainerApplicable(Protocol):
    def apply(self, actions_container: _ActionsContainer, name: str) -> None: ...


@dataclass(kw_only=True)
class BaseArgument(ABC, ContainerApplicable):
    name: str
    help: str | None = None

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    def apply(self, actions_container: _ActionsContainer, name: str) -> None:
        args = self.get_argparse_args()
        kwargs = self.get_argparse_kwargs()
        actions_container.add_argument(*args, **kwargs)

    @abstractmethod
    def get_argparse_args(self) -> list[str]: ...

    def get_argparse_kwargs(self) -> dict[str, Any]:
        kwargs = {}
        if self.help is not None:
            kwargs["help"] = self.help
        return kwargs


@dataclass
class Flag(BaseArgument):
    short: str | None = None
    short_only: bool = False
    no_flag: bool = False

    @property
    def display_name(self) -> str:
        if self.no_flag:
            return f"--no-{self.name.replace("_", "-")}"
        return f"--{self.name.replace("_", "-")}"

    def get_argparse_args(self) -> list[str]:
        if self.short_only:
            if self.short is not None:
                return [self.short]
            return [f"-{self.name}"]

        args = [self.display_name]
        if self.short is not None:
            args.insert(0, self.short)
        return args

    def get_argparse_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs()
        kwargs["action"] = "store_true" if not self.no_flag else "store_false"

        kwargs["dest"] = self.name
        return kwargs


class TriFlag(ContainerApplicable):
    name: str

    @property
    def display_name(self) -> str:
        return f"--(no-){self.name.replace("_", "-")}"

    def apply(self, actions_container: _ActionsContainer, name: str) -> None:
        # if actions_container is not an mx group, make it one, argparse
        # doesn't support mx group nesting
        if not isinstance(actions_container, _MutuallyExclusiveGroup):
            actions_container = actions_container.add_mutually_exclusive_group()

        name = name.replace("_", "-")
        actions_container.add_argument(f"--{name}", action="store_true")
        actions_container.add_argument(f"--no-{name}", action="store_true")


@dataclass(kw_only=True)
class BaseValueArgument[T](BaseArgument):
    default: T | str | Void = void
    converter: Callable[[str], T] | None = None
    choices: Collection[T] | None = None
    nargs: Literal["?", "*", "+"] | None = None
    optional: bool = False
    metavar: str | None = None

    def get_argparse_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs()

        if self.default is not void:
            kwargs["default"] = self.default
        if self.choices is not None:
            kwargs["choices"] = self.choices
        if self.nargs is not None:
            kwargs["nargs"] = self.nargs
        if self.metavar is not None:
            kwargs["metavar"] = self.metavar

        return kwargs


@dataclass
class Positional[T](BaseValueArgument[T]):
    @property
    def display_name(self) -> str:
        return self.name

    def get_argparse_args(self) -> list[str]:
        return [self.name]

    def get_argparse_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs()

        if self.nargs is None and (self.optional or self.default is not void):
            kwargs["nargs"] = "?"

        return kwargs


@dataclass
class Option[T](BaseValueArgument[T]):
    dest: str | None = None
    short: str | None = None
    short_only: bool = False
    append: bool = False

    @property
    def display_name(self) -> str:
        return f"--{(self.name).replace("_", "-")}"

    def get_argparse_args(self) -> list[str]:
        if self.short_only:
            if self.short is not None:
                return [self.short]
            return [f"-{self.name}"]

        args = [self.display_name]
        if self.short is not None:
            args.insert(0, self.short)
        return args

    def get_argparse_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs()

        if self.dest is not None:
            kwargs["dest"] = self.dest
        if not self.optional and self.default is void:
            kwargs["required"] = True
        if self.append:
            kwargs["action"] = "append"

        # append with default is handled manually later, replace with empty list for now because
        # argparse always uses default instead of using it only when no arguments are provided
        if self.append:
            kwargs["default"] = []

        return kwargs


@dataclass(eq=False)
class MxGroup:
    arguments: dict[str, BaseArgument] = field(default_factory=dict)
    required: bool = False


@dataclass
class Subparsers:
    sub_parsers: dict[str, "Parser"] = field(default_factory=dict)
    required: bool = False
