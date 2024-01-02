from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin
import argparse
import inspect

from arcparse.converters import itemwise

from ._partial_arguments import (
    BasePartialArgument,
    PartialFlag,
    PartialMxGroup,
    PartialOption,
    PartialSubparsers,
    PartialTriFlag,
)
from ._typehints import extract_optional_type, extract_subparsers_from_typehint
from .arguments import (
    BaseArgument,
    BaseValueArgument,
    MxGroup,
    Subparsers,
    TriFlag,
    void,
)
from .errors import InvalidArgument, InvalidParser, InvalidTypehint


__all__ = ["Parser", "RootParser"]


@dataclass
class Parser[T]:
    shape: type[T]
    arguments: dict[str, BaseArgument] = field(default_factory=dict)
    mx_groups: list[MxGroup] = field(default_factory=list)

    @property
    def all_arguments(self) -> Iterator[tuple[str, BaseArgument]]:
        yield from self.arguments.items()
        for mx_group in self.mx_groups:
            yield from mx_group.arguments.items()

    def apply(self, actions_container: argparse._ActionsContainer) -> None:
        for name, argument in self.arguments.items():
            argument.apply(actions_container, name)

        for mx_group in self.mx_groups:
            group = actions_container.add_mutually_exclusive_group(required=mx_group.required)
            for name, argument in mx_group.arguments.items():
                argument.apply(group, name)


@dataclass
class RootParser[T]:
    parser: Parser[T]
    subparsers: tuple[str, Subparsers] | None = None

    @property
    def shape(self) -> type[T]:
        return self.parser.shape

    @property
    def all_arguments(self) -> Iterator[tuple[str, BaseArgument]]:
        yield from self.parser.all_arguments

        if self.subparsers is not None:
            for subparser in self.subparsers[1].sub_parsers.values():
                yield from subparser.all_arguments

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

        ret = parsed.__dict__
        if self.subparsers is not None:
            name, subparsers = self.subparsers

            # optional subparsers will result in `dict[name]` being `None`
            if chosen_subparser := getattr(parsed, name, None):
                sub_parser = subparsers.sub_parsers[chosen_subparser]
                ret[name] = _construct_object_with_parsed(sub_parser, ret)

        return _construct_object_with_parsed(self.parser, ret)


def _construct_object_with_parsed[T](parser: Parser[T], parsed: dict[str, Any]) -> T:
    # apply argument converters
    for name, argument in parser.all_arguments:
        if not isinstance(argument, BaseValueArgument) or argument.converter is None:
            continue

        value = parsed.get(name, argument.default)
        if isinstance(argument.converter, itemwise):
            assert isinstance(value, list)
            parsed[name] = [
                argument.converter(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            parsed[name] = argument.converter(value) if isinstance(value, str) else value

    # reduce tri_flags
    tri_flag_names = [name for name, arg in parser.all_arguments if isinstance(arg, TriFlag)]
    _reduce_tri_flags(parsed, tri_flag_names)

    return _instantiate_from_dict(parser.shape, parsed)


def _instantiate_from_dict[T](cls: type[T], dict_: dict[str, Any]) -> T:
    values = {}
    annotations = inspect.get_annotations(cls, eval_str=True)
    for name in annotations.keys():
        values[name] = dict_.pop(name)

    obj = cls()
    obj.__dict__ = values
    return obj


def _reduce_tri_flags(dict_: dict[str, Any], tri_flag_names: list[str]) -> None:
    for name in tri_flag_names:
        no_flag_name = f"no_{name}"
        yes_case = dict_[name]
        no_case = dict_[no_flag_name]
        assert not yes_case or not no_case

        del dict_[no_flag_name]
        if yes_case:
            dict_[name] = True
        elif no_case:
            dict_[name] = False
        else:
            dict_[name] = None


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
        elif extract_optional_type(typehint) == bool:
            argument = PartialTriFlag()
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
        argument = partial_argument.resolve_with_typehint(name, typehint)

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
