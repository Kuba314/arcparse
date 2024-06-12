from abc import ABC, abstractmethod
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from enum import StrEnum
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin
import re

from arcparse.errors import InvalidArgument, InvalidTypehint, MissingConverter

from ._typehints import (
    extract_collection_type,
    extract_literal_strings,
    extract_optional_type,
    extract_type_from_typehint,
)
from .arguments import (
    BaseValueArgument,
    ContainerApplicable,
    Flag,
    Option,
    Positional,
    TriFlag,
    Void,
    void,
)
from .converters import itemwise


@dataclass(kw_only=True, eq=False)
class PartialMxGroup:
    required: bool = False


@dataclass(kw_only=True)
class BasePartialArgument[R: ContainerApplicable](ABC):
    mx_group: PartialMxGroup | None = None

    @abstractmethod
    def resolve_with_typehint(self, name: str, typehint: type) -> R:
        ...

    def resolve_to_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        return {}


@dataclass(kw_only=True)
class BaseSinglePartialArgument[R: ContainerApplicable](BasePartialArgument[R]):
    help: str | None = None

    def resolve_to_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(name, typehint)
        if self.help is not None:
            kwargs["help"] = self.help
        return kwargs


@dataclass(kw_only=True)
class BasePartialValueArgument[T, R: BaseValueArgument](BaseSinglePartialArgument[R]):
    default: T | str | Void = void
    choices: Collection[str] | None = None
    converter: Callable[[str], T] | None = None
    name_override: str | None = None
    at_least_one: bool = False

    def resolve_to_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(name, typehint)

        type_ = extract_type_from_typehint(typehint)
        if self.converter is None:
            if type_ is bool:
                raise InvalidTypehint("Arguments yielding a value cannot be typed as `bool`")
            elif getattr(type_, "_is_protocol", False):
                raise MissingConverter("Argument with no converter can't be typed as a Protocol subclass")
            if get_origin(typehint) in {Union, UnionType}:
                union_args = get_args(typehint)
                if len(union_args) > 2 or NoneType not in union_args:
                    raise InvalidTypehint("Union can be used only for optional arguments (length of 2, 1 of them being None)")

            if type_ is not str and get_origin(type_) != Literal:
                if extract_collection_type(typehint):
                    self.converter = itemwise(type_)  # type: ignore (list[T@itemwise] somehow incompatible with T@_BaseValueArgument)
                elif type_ == re.Pattern:
                    self.converter = re.compile  # type: ignore (somehow incompatible)
                elif issubclass(type_, StrEnum):
                    self.choices = set(map(str, type_))
                else:
                    self.converter = type_

        choices = self.choices
        if literal_choices := extract_literal_strings(type_):
            if self.choices is None:
                choices = literal_choices
            elif not (set(self.choices) <= set(literal_choices)):
                raise InvalidArgument("explicit choices have to be a subset of target literal typehint")

        if self.converter is not None:
            kwargs["converter"] = self.converter
        if self.default is not void:
            kwargs["default"] = self.default
        if choices is not None:
            kwargs["choices"] = choices

        if extract_optional_type(typehint):
            kwargs["optional"] = True
        elif extract_collection_type(typehint) and not self.at_least_one:
            kwargs["default"] = []

        return kwargs


@dataclass
class PartialPositional[T](BasePartialValueArgument[T, Positional]):
    def resolve_with_typehint(self, name: str, typehint: type) -> Positional:
        kwargs = self.resolve_to_kwargs(name, typehint)
        return Positional(**kwargs)

    def resolve_to_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(name, typehint)

        type_is_optional = bool(extract_optional_type(typehint))
        type_is_collection = bool(extract_collection_type(typehint))
        optional = type_is_optional or type_is_collection or self.default is not void
        if not optional and self.mx_group is not None:
            raise InvalidArgument("Arguments in mutually exclusive group have to have a default")

        if self.name_override is not None:
            if self.choices is None:  # choices generate custom `{foo,bar}` metavar in argparse
                kwargs["metavar"] = self.name_override

        if type_is_collection and (self.converter is None or isinstance(self.converter, itemwise)):
            kwargs["nargs"] = "+" if self.at_least_one else "*"
            kwargs["metavar"] = self.name_override

        return kwargs


@dataclass
class PartialOption[T](BasePartialValueArgument[T, Option]):
    short: str | None = None
    short_only: bool = False
    append: bool = False

    def resolve_with_typehint(self, name: str, typehint: type) -> Option:
        if self.short_only and self.short is None and len(name) > 1:
            raise InvalidArgument(f"Argument \"{name}\" requested short_only but name is longer than 1 character and no short-hand was specified")

        kwargs = self.resolve_to_kwargs(name, typehint)
        return Option(**kwargs)

    def resolve_to_kwargs(self, name: str, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(name, typehint)
        kwargs["short"] = self.short
        kwargs["short_only"] = self.short_only

        if extract_collection_type(typehint) and isinstance(self.converter, itemwise):
            if self.append:
                kwargs["append"] = True
            else:
                kwargs["nargs"] = "+" if self.at_least_one else "*"

        if self.name_override is not None:
            kwargs["name"] = self.name_override
            kwargs["dest"] = name
            if self.choices is None:  # choices generate custom `{foo,bar}` metavar in argparse
                kwargs["metavar"] = self.name_override.replace("-", "_").upper()
        elif self.short_only and self.short is not None:
            kwargs["dest"] = name
        else:
            kwargs["name"] = name

        type_is_optional = bool(extract_optional_type(typehint))
        type_is_collection = bool(extract_collection_type(typehint))
        required = (not (type_is_optional or type_is_collection)) or self.at_least_one
        if not required:
            kwargs["optional"] = True
        elif self.mx_group is not None:
            raise InvalidArgument("Arguments in mutually exclusive group have to have a default")

        return kwargs


@dataclass
class PartialFlag(BaseSinglePartialArgument[Flag]):
    short: str | None = None
    short_only: bool = False
    no_flag: bool = False

    def resolve_with_typehint(self, name: str, typehint: type) -> Flag:
        if self.short_only and self.short is None and len(name) > 1:
            raise InvalidArgument(f"Argument \"{name}\" requested short_only but name is longer than 1 character and no short-hand was specified")

        kwargs = self.resolve_to_kwargs(name, typehint)
        kwargs["short"] = self.short
        kwargs["short_only"] = self.short_only
        kwargs["no_flag"] = self.no_flag
        return Flag(**kwargs)


class PartialTriFlag(BasePartialArgument[TriFlag]):
    def resolve_with_typehint(self, name: str, typehint: type) -> TriFlag:
        return TriFlag()


@dataclass
class PartialSubparsers[T]:
    names: list[str]
    shapes: list[T] = field(default_factory=list)
