from __future__ import annotations

from argparse import ArgumentParser, _ActionsContainer
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin
import inspect
import re

from ._arguments import MxGroup, _BaseArgument, _BaseValueArgument, _Flag, _Option, void
from ._typehints import (
    extract_collection_type,
    extract_literal_strings,
    extract_optional_type,
    extract_subparsers_from_typehint,
    extract_type_from_typehint,
)
from .converters import itemwise
from .errors import InvalidArgument, InvalidParser, InvalidTypehint, MissingConverter


type NameTypeArg[TArg: "_BaseArgument | _Subparsers"] = tuple[str, type, TArg]


def _instantiate_from_dict[T](cls: type[T], dict_: dict[str, Any]) -> T:
    values = {}
    annotations = inspect.get_annotations(cls, eval_str=True)
    for name in annotations.keys():
        values[name] = dict_.pop(name)

    obj = cls()
    obj.__dict__ = values
    return obj


def _collect_arguments(cls: type) -> list[NameTypeArg[_BaseArgument]]:
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
            if isinstance(value, _BaseArgument):
                raise InvalidTypehint(f"Argument {key} is missing a type-hint and would be ignored")
            continue

        typehint, _ = all_params[key]
        all_params[key] = (typehint, value)

    # construct arguments
    arguments: list[NameTypeArg] = []
    for name, (typehint, value) in all_params.items():
        if isinstance(value, _Subparsers):
            continue

        if get_origin(typehint) in {Union, UnionType}:
            union_args = get_args(typehint)
            if len(union_args) > 2 or NoneType not in union_args:
                raise InvalidTypehint("Union can be used only for optional arguments (length of 2, 1 of them being None)")

        if isinstance(value, _BaseArgument):
            argument = value
        else:
            argument = _construct_argument(typehint, value)

        arguments.append((name, typehint, argument))

    return arguments


def _construct_argument(typehint: type, default: Any) -> _BaseArgument:
    if typehint is bool:
        if default is not void:
            raise InvalidArgument("defaults don't make sense for flags")
        return _Flag()

    actual_type = extract_type_from_typehint(typehint)
    if actual_type is bool:
        raise MissingConverter("Can't construct argument with inner type bool, conversion would be always True")
    elif getattr(actual_type, "_is_protocol", False):
        raise MissingConverter("Argument with no converter can't be typed as a Protocol subclass")

    if type_ := extract_collection_type(typehint):
        converter = itemwise(type_)
    else:
        converter = actual_type

    if choices := extract_literal_strings(actual_type):
        return _Option(default=default, choices=choices)
    elif issubclass(actual_type, StrEnum):
        return _Option(default=default, choices=list(actual_type), converter=converter)
    elif actual_type == re.Pattern:
        return _Option(default=default, converter=re.compile)

    return _Option(default=default, converter=converter if actual_type is not str else None)


def _check_argument_sanity(name: str, typehint: type, arg: _BaseArgument) -> None:
    if isinstance(arg, _BaseValueArgument) and extract_type_from_typehint(typehint) is bool and arg.converter is None:
        raise InvalidTypehint(f"Argument \"{name}\" yielding a value can't be typed as `bool`")

    if arg.mx_group is not None and isinstance(arg, _BaseValueArgument) and extract_optional_type(typehint) is None and arg.default is void:
        raise InvalidArgument(f"Argument \"{name}\" in mutually exclusive group has to have a default")


def _collect_subparsers(cls: type) -> NameTypeArg[_Subparsers] | None:
    all_subparsers = [(key, value) for key, value in vars(cls).items() if isinstance(value, _Subparsers)]
    if not all_subparsers:
        return None

    elif len(all_subparsers) > 1:
        raise InvalidParser(f"Multiple subparsers definitions found on {cls}")

    name, subparsers = all_subparsers[0]
    if not (typehint := inspect.get_annotations(cls, eval_str=True)[name]):
        raise InvalidTypehint("subparsers have to be type-hinted")

    if not extract_subparsers_from_typehint(typehint):
        raise InvalidTypehint(f"Unable to extract subparser types from {typehint}, expected a non-empty union of ArcParser types")

    return (name, typehint, subparsers)


@dataclass
class _Subparsers:
    names: list[str]

    def apply(
        self,
        parser: ArgumentParser,
        name: str,
        typehint: type,
    ) -> None:
        if not (subparser_types := extract_subparsers_from_typehint(typehint)):
            raise InvalidTypehint(f"Unable to extract subparser types from {typehint}, expected a non-empty union of ArcParser types")

        subparsers_kwargs: dict = {"dest": name}
        if NoneType not in subparser_types:
            subparsers_kwargs["required"] = True
        subparsers = parser.add_subparsers(**subparsers_kwargs)

        nonnull_subparser_types: list[type[_Parser]] = [
            typ for typ in subparser_types if typ is not NoneType
        ]  # type: ignore  (NoneType is getting confused with None)

        for name, subparser_type in zip(self.names, nonnull_subparser_types):
            subparser = _make_parser(subparser_type)
            subparser.apply(subparsers.add_parser(name))


class _Parser[T]:
    def __init__(
        self,
        cls: type[T],
        arguments: list[NameTypeArg[_BaseArgument]] | None = None,
        mx_groups: dict[MxGroup, list[NameTypeArg[_BaseArgument]]] | None = None,
        subparsers: NameTypeArg[_Subparsers] | None = None,
    ):
        self._cls = cls
        self._arguments = arguments if arguments is not None else {}
        self._mx_groups = mx_groups if mx_groups is not None else {}
        self._subparsers = subparsers

        assert all(arg.mx_group is None for _, _, arg in self._arguments)

    def parse(self, args: Sequence[str] | None = None) -> T:
        parser = ArgumentParser()
        self.apply(parser)
        if self._subparsers is not None:
            name, typehint, subparsers = self._subparsers
            subparsers.apply(parser, name, typehint)
        parsed = parser.parse_args(args)

        ret = parsed.__dict__.copy()
        if self._subparsers is not None:
            name, typehint, subparsers = self._subparsers

            # optional subparsers will result in `dict[name]` being `None`
            subshape_classes = extract_subparsers_from_typehint(typehint)
            assert subshape_classes is not None
            if chosen_subparser := getattr(parsed, name):
                subshape_class = subshape_classes[subparsers.names.index(chosen_subparser)]
                ret[name] = _instantiate_from_dict(subshape_class, parsed.__dict__)

        return _instantiate_from_dict(self._cls, ret)

    def apply(self, actions_container: _ActionsContainer) -> None:
        for (name, typehint, argument) in self._arguments:
            argument.apply(actions_container, name, typehint)

        for mx_group, arguments in self._mx_groups.items():
            group = actions_container.add_mutually_exclusive_group(required=mx_group.required)
            for name, typehint, arg in arguments:
                arg.apply(group, name, typehint)


def _make_parser[T](cls: type[T]) -> _Parser[T]:
    arguments = _collect_arguments(cls)
    subparsers = _collect_subparsers(cls)

    for name, type, arg in arguments:
        _check_argument_sanity(name, type, arg)

    mx_groups: dict[MxGroup, list[NameTypeArg[_BaseArgument]]] = {}
    for argument in arguments:
        if argument[2].mx_group is not None:
            mx_groups.setdefault(argument[2].mx_group, []).append(argument)
    arguments = [argument for argument in arguments if argument[2].mx_group is None]

    return _Parser(cls, arguments, mx_groups, subparsers)


def arcparser[T](cls: type[T]) -> _Parser[T]:
    return _make_parser(cls)


def subparsers(*args: str) -> Any:
    return _Subparsers(names=list(args))
