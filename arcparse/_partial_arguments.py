from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, get_origin
import re

from arcparse.errors import InvalidArgument, InvalidTypehint, MissingConverter

from ._arguments import BaseArgument, Flag, NoFlag, Option, Positional, Void, void
from ._typehints import (
    extract_collection_type,
    extract_optional_type,
    extract_type_from_typehint,
)
from .converters import itemwise


@dataclass(kw_only=True, eq=False)
class _PartialMxGroup:
    required: bool = False


@dataclass(kw_only=True)
class _BasePartialArgument[TResolved: BaseArgument](ABC):
    mx_group: _PartialMxGroup | None = None
    help: str | None = None

    @abstractmethod
    def resolve_with_typehint(self, typehint: type) -> TResolved:
        ...

    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        return {
            "help": self.help,
        }



@dataclass(kw_only=True)
class _BasePartialValueArgument[T](_BasePartialArgument):
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

    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(typehint)

        if self.converter is None:
            type_ = extract_type_from_typehint(typehint)
            if type_ is bool:
                raise InvalidTypehint("Arguments yielding a value cannot be typed as `bool`")
            elif getattr(type_, "_is_protocol", False):
                raise MissingConverter("Argument with no converter can't be typed as a Protocol subclass")

            if type_ is not str and get_origin(type_) != Literal:
                if extract_collection_type(typehint):
                    self.converter = itemwise(type_)  # type: ignore (list[T@itemwise] somehow incompatible with T@_BaseValueArgument)
                elif type_ == re.Pattern:
                    self.converter = re.compile  # type: ignore (somehow incompatible)
                else:
                    self.converter = type_

        if self.converter is not None:
            kwargs["converter"] = self.converter
        if self.default is not void:
            kwargs["default"] = self.default
        if self.choices is not None:
            kwargs["choices"] = self.choices

        if self.need_multiple(typehint) and not self.at_least_one and self.default is void:
            kwargs["default"] = []

        return kwargs


@dataclass
class _PartialPositional[T](_BasePartialValueArgument[T]):
    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(typehint)

        type_is_optional = bool(extract_optional_type(typehint))
        type_is_collection = bool(extract_collection_type(typehint))
        optional = type_is_optional or type_is_collection or self.default is not void
        if not optional and self.mx_group is not None:
            raise InvalidArgument("Arguments in mutually exclusive group have to have a default")

        if self.name_override is not None:
            kwargs["metavar"] = self.name_override

        if self.need_multiple(typehint):
            kwargs["nargs"] = "+" if self.at_least_one else "*"
            kwargs["metavar"] = self.name_override  # if self.name_override is not None else name.upper()
        elif optional:
            kwargs["nargs"] = "?"

        return kwargs

    def resolve_with_typehint(self, typehint: type) -> Positional:
        kwargs = self.resolve_to_kwargs(typehint)
        return Positional(**kwargs)


@dataclass
class _PartialOption[T](_BasePartialValueArgument[T]):
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

    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(typehint)
        kwargs["short"] = self.short
        kwargs["short_only"] = self.short_only

        if self.need_multiple(typehint):
            if self.append:
                kwargs["append"] = True
            else:
                kwargs["nargs"] = "+" if self.at_least_one else "*"

        if self.name_override is not None:
            kwargs["metavar"] = self.name_override.replace("-", "_").upper()

        type_is_optional = bool(extract_optional_type(typehint))
        type_is_collection = bool(extract_collection_type(typehint))
        required = (not (type_is_optional or type_is_collection) and self.default is void) or self.at_least_one
        if required:
            if self.mx_group is not None:
                raise InvalidArgument("Arguments in mutually exclusive group have to have a default")
            kwargs["required"] = True

        return kwargs

    def resolve_with_typehint(self, typehint: type) -> Option:
        kwargs = self.resolve_to_kwargs(typehint)
        return Option(**kwargs)


@dataclass
class _PartialFlag(_BasePartialArgument):
    short: str | None = None
    short_only: bool = False

    def resolve_with_typehint(self, typehint: type) -> Flag:
        kwargs = self.resolve_to_kwargs(typehint)
        kwargs["short"] = self.short
        kwargs["short_only"] = self.short_only
        return Flag(**kwargs)


@dataclass
class _PartialNoFlag(_BasePartialArgument):
    def resolve_with_typehint(self, typehint: type) -> NoFlag:
        kwargs = self.resolve_to_kwargs(typehint)
        return NoFlag(**kwargs)


@dataclass
class _PartialSubparsers:
    names: list[str]
