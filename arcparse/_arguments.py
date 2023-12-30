from abc import ABC, abstractmethod
from argparse import Action, _ActionsContainer, _MutuallyExclusiveGroup
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol


if TYPE_CHECKING:
    from ._parser import Parser


class Void:
    pass

void = Void()


class ContainerApplicable(Protocol):
    def apply(self, actions_container: _ActionsContainer, name: str) -> Action:
        ...


class BaseSingleArgument(ContainerApplicable, ABC):
    def apply(self, actions_container: _ActionsContainer, name: str) -> Action:
        args = self.get_argparse_args(name)
        kwargs = self.get_argparse_kwargs(name)
        return actions_container.add_argument(*args, **kwargs)

    @abstractmethod
    def get_argparse_args(self, name: str) -> list[str]:
        ...

    @abstractmethod
    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        ...


@dataclass(kw_only=True)
class BaseArgument(BaseSingleArgument):
    help: str | None = None

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = {}
        if self.help is not None:
            kwargs["help"] = self.help
        return kwargs


@dataclass
class Flag(BaseArgument):
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
class NoFlag(BaseArgument):
    def get_argparse_args(self, name: str) -> list[str]:
        return [f"--no-{name.replace("_", "-")}"]

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)
        kwargs["action"] = "store_false"

        kwargs["dest"] = name
        return kwargs


class TriFlag(ContainerApplicable):
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
    metavar: str | None = None

    def get_argparse_kwargs(self, name: str) -> dict[str, Any]:
        kwargs = super().get_argparse_kwargs(name)

        if self.default is not void:
            kwargs["default"] = self.default
        if self.converter is not None:
            kwargs["type"] = self.converter
        if self.choices is not None:
            kwargs["choices"] = self.choices
        if self.nargs is not None:
            kwargs["nargs"] = self.nargs
        if self.metavar is not None:
            kwargs["metavar"] = self.metavar

        return kwargs


@dataclass
class Positional[T](BaseValueArgument[T]):
    def get_argparse_args(self, name: str) -> list[str]:
        return [name]


@dataclass
class Option[T](BaseValueArgument[T]):
    name_override: str | None = None
    short: str | None = None
    short_only: bool = False
    required: bool = False
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

        if self.name_override is not None or self.short_only:
            kwargs["dest"] = name
        if self.required:
            kwargs["required"] = True
        if self.append:
            kwargs["action"] = "append"

        return kwargs


@dataclass(eq=False)
class MxGroup:
    arguments: dict[str, BaseArgument] = field(default_factory=dict)
    required: bool = False


@dataclass
class Subparsers:
    sub_parsers: dict[str, "Parser"] = field(default_factory=dict)
    required: bool = False
