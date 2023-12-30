from abc import ABC, abstractmethod
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Any, Literal, get_origin
import re

from arcparse.errors import InvalidArgument, InvalidTypehint, MissingConverter

from ._arguments import (
    BaseValueArgument,
    ContainerApplicable,
    Flag,
    NoFlag,
    Option,
    Positional,
    TriFlag,
    Void,
    void,
)
from ._typehints import (
    extract_collection_type,
    extract_literal_strings,
    extract_optional_type,
    extract_type_from_typehint,
)
from .converters import itemwise


@dataclass(kw_only=True, eq=False)
class PartialMxGroup:
    required: bool = False


@dataclass(kw_only=True)
class BasePartialArgument[R: ContainerApplicable](ABC):
    mx_group: PartialMxGroup | None = None

    @abstractmethod
    def resolve_with_typehint(self, typehint: type) -> R:
        ...

    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        return {}


@dataclass(kw_only=True)
class BaseSinglePartialArgument[R: ContainerApplicable](BasePartialArgument[R]):
    help: str | None = None

    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        return super().resolve_to_kwargs(typehint) | {
            "help": self.help,
        }


@dataclass(kw_only=True)
class BasePartialValueArgument[T, R: BaseValueArgument](BaseSinglePartialArgument[R]):
    default: T | str | Void = void
    choices: Collection[str] | None = None
    converter: Callable[[str], T] | None = None
    name_override: str | None = None
    at_least_one: bool = False

    def resolve_to_kwargs(self, typehint: type) -> dict[str, Any]:
        kwargs = super().resolve_to_kwargs(typehint)

        type_ = extract_type_from_typehint(typehint)
        if self.converter is None:
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

        if self.need_multiple(typehint) and not self.at_least_one and self.default is void:
            kwargs["default"] = []

        return kwargs

    def need_multiple(self, typehint: type) -> bool:
        return (
            (self.converter is None and extract_collection_type(typehint) is not None)
            or isinstance(self.converter, itemwise)
        )


@dataclass
class PartialPositional[T](BasePartialValueArgument[T, Positional]):
    def resolve_with_typehint(self, typehint: type) -> Positional:
        kwargs = self.resolve_to_kwargs(typehint)
        return Positional(**kwargs)

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
            kwargs["metavar"] = self.name_override
        elif optional:
            kwargs["nargs"] = "?"

        return kwargs


@dataclass
class PartialOption[T](BasePartialValueArgument[T, Option]):
    short: str | None = None
    short_only: bool = False
    append: bool = False

    def resolve_with_typehint(self, typehint: type) -> Option:
        kwargs = self.resolve_to_kwargs(typehint)
        return Option(**kwargs)

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


@dataclass
class PartialFlag(BaseSinglePartialArgument[Flag]):
    short: str | None = None
    short_only: bool = False

    def resolve_with_typehint(self, typehint: type) -> Flag:
        kwargs = self.resolve_to_kwargs(typehint)
        kwargs["short"] = self.short
        kwargs["short_only"] = self.short_only
        return Flag(**kwargs)


@dataclass
class PartialNoFlag(BaseSinglePartialArgument[NoFlag]):
    def resolve_with_typehint(self, typehint: type) -> NoFlag:
        kwargs = self.resolve_to_kwargs(typehint)
        return NoFlag(**kwargs)


class PartialTriFlag(BasePartialArgument[TriFlag]):
    def resolve_with_typehint(self, typehint: type) -> TriFlag:
        return TriFlag()


@dataclass
class PartialSubparsers:
    names: list[str]
