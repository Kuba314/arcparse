from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin
import argparse
import inspect
import re

from ._arguments import BaseArgument, Flag, MxGroup, Option, Subparsers, void
from ._partial_arguments import (
    BasePartialArgument,
    PartialFlag,
    PartialMxGroup,
    PartialOption,
    PartialSubparsers,
)
from ._typehints import (
    extract_collection_type,
    extract_literal_strings,
    extract_subparsers_from_typehint,
    extract_type_from_typehint,
)
from .converters import itemwise
from .errors import InvalidArgument, InvalidParser, InvalidTypehint, MissingConverter


@dataclass
class Parser[T]:
    shape: type[T]
    arguments: dict[str, BaseArgument] = field(default_factory=dict)
    mx_groups: list[MxGroup] = field(default_factory=list)

    def apply(self, actions_container: argparse._ActionsContainer) -> None:
        for name, argument in self.arguments.items():
            argument.apply(actions_container, name)

        for mx_group in self.mx_groups:
            group = actions_container.add_mutually_exclusive_group(required=mx_group.required)
            for name, argument in mx_group.arguments.items():
                argument.apply(group, name)


@dataclass
class RootParser[T]:
    parser: Parser
    subparsers: tuple[str, Subparsers] | None = None

    def parse(self, args: Sequence[str] | None = None) -> T:
        ap_parser = argparse.ArgumentParser()
        self.parser.apply(ap_parser)
        if self.subparsers is not None:
            name, subparsers = self.subparsers
            ap_subparsers = ap_parser.add_subparsers(dest=name, required=subparsers.required)
            for name, subparser in subparsers.sub_parsers.items():
                ap_subparser = ap_subparsers.add_parser(name)
                subparser.apply(ap_subparser)

        parsed = ap_parser.parse_args(args)

        ret = parsed.__dict__.copy()
        if self.subparsers is not None:
            name, subparsers = self.subparsers

            # optional subparsers will result in `dict[name]` being `None`
            if chosen_subparser := getattr(parsed, name, None):
                sub_parser = subparsers.sub_parsers[chosen_subparser]
                sub_parser.shape
                ret[name] = _instantiate_from_dict(sub_parser.shape, parsed.__dict__)

        return _instantiate_from_dict(self.parser.shape, ret)


def _instantiate_from_dict[T](cls: type[T], dict_: dict[str, Any]) -> T:
    values = {}
    annotations = inspect.get_annotations(cls, eval_str=True)
    for name in annotations.keys():
        values[name] = dict_.pop(name)

    obj = cls()
    obj.__dict__ = values
    return obj


def _collect_partial_arguments(cls: type) -> dict[str, tuple[type, BasePartialArgument]]:
    # collect declared typehints
    all_params: dict[str, tuple[type, Any]] = {
        name: (typehint, void)
        for name, typehint in inspect.get_annotations(cls, eval_str=True).items()
    }

    # collect declared defaults
    for key, value in vars(cls).items():
        # skip methods, properties and dunder attributes
        if callable(value) or isinstance(value, property) or (key.startswith("__") and key.endswith("__")):
            continue

        # ignore untyped class variables un
        if key not in all_params:
            if isinstance(value, BasePartialArgument):
                raise InvalidTypehint(f"Argument {key} is missing a type-hint and would be ignored")
            continue

        typehint, _ = all_params[key]
        all_params[key] = (typehint, value)

    # construct arguments
    arguments: dict[str, tuple[type, BasePartialArgument]] = {}
    for name, (typehint, value) in all_params.items():
        if isinstance(value, PartialSubparsers):
            continue

        if get_origin(typehint) in {Union, UnionType}:
            union_args = get_args(typehint)
            if len(union_args) > 2 or NoneType not in union_args:
                raise InvalidTypehint("Union can be used only for optional arguments (length of 2, 1 of them being None)")

        if isinstance(value, BasePartialArgument):
            argument = value
        elif typehint is bool:
            if value is not void:
                raise InvalidArgument("defaults don't make sense for flags")
            argument = PartialFlag()
        else:
            argument = PartialOption(default=value)
        arguments[name] = (typehint, argument)

    return arguments


def _collect_subparsers(shape: type) -> tuple[str, type, PartialSubparsers] | None:
    all_subparsers = [(key, value) for key, value in vars(shape).items() if isinstance(value, PartialSubparsers)]
    if not all_subparsers:
        return None

    elif len(all_subparsers) > 1:
        raise InvalidParser(f"Multiple subparsers definitions found on {shape}")

    name, partial_subparsers = all_subparsers[0]
    if not (typehint := inspect.get_annotations(shape, eval_str=True).get(name)):
        raise InvalidTypehint("subparsers have to be type-hinted")

    return name, typehint, partial_subparsers


def _make_parser[T](shape: type[T]) -> Parser[T]:
    arguments = {}
    mx_groups: dict[PartialMxGroup, MxGroup] = {}
    for name, (typehint, partial_argument) in _collect_partial_arguments(shape).items():
        mx_group = partial_argument.mx_group
        argument = partial_argument.resolve_with_typehint(typehint)

        if mx_group is None:
            arguments[name] = argument
        else:
            if mx_group not in mx_groups:
                mx_groups[mx_group] = MxGroup(required=mx_group.required)
            mx_groups[mx_group].arguments[name] = argument

    return Parser(
        shape,
        arguments,
        list(mx_groups.values()),
    )


def _make_root_parser[T](shape: type[T]) -> RootParser[T]:
    match _collect_subparsers(shape):
        case (name, typehint, partial_subparsers):
            subshapes = extract_subparsers_from_typehint(typehint)
            subparsers_by_name = {
                name: _make_parser(subshape)
                for name, subshape in zip(partial_subparsers.names, subshapes)
            }
            subparsers = (name, Subparsers(subparsers_by_name, required=NoneType not in subshapes))
        case _:
            subparsers = None

    return RootParser(
        _make_parser(shape),
        subparsers,
    )


def arcparser[T](shape: type[T]) -> RootParser[T]:
    return _make_root_parser(shape)
