from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any
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
from ._typehints import (
    extract_optional_type,
    extract_subparsers_from_typehint,
    union_contains_none,
)
from .arguments import (
    BaseArgument,
    BaseValueArgument,
    MxGroup,
    Subparsers,
    TriFlag,
    void,
)
from .errors import InvalidArgument, InvalidParser, InvalidTypehint


__all__ = ["Parser"]


@dataclass
class Parser[T]:
    shape: type[T]
    arguments: dict[str, BaseArgument] = field(default_factory=dict)
    mx_groups: list[MxGroup] = field(default_factory=list)
    subparsers: tuple[str, Subparsers] | None = None

    @property
    def all_arguments(self) -> Iterator[tuple[str, BaseArgument]]:
        yield from self.arguments.items()
        for mx_group in self.mx_groups:
            yield from mx_group.arguments.items()

        if self.subparsers is not None:
            for subparser in self.subparsers[1].sub_parsers.values():
                yield from subparser.all_arguments

    def parse(self, args: Sequence[str] | None = None) -> T:
        ap_parser = argparse.ArgumentParser()
        self.apply(ap_parser)

        parsed = ap_parser.parse_args(args).__dict__

        # reduce tri_flags
        tri_flag_names = [name for name, arg in self.all_arguments if isinstance(arg, TriFlag)]
        _reduce_tri_flags(parsed, tri_flag_names)

        return self._construct_object_with_parsed(parsed)

    def apply(self, ap_parser: argparse.ArgumentParser) -> None:
        for name, argument in self.arguments.items():
            argument.apply(ap_parser, name)

        for mx_group in self.mx_groups:
            group = ap_parser.add_mutually_exclusive_group(required=mx_group.required)
            for name, argument in mx_group.arguments.items():
                argument.apply(group, name)

        if self.subparsers is not None:
            name, subparsers = self.subparsers
            ap_subparsers = ap_parser.add_subparsers(dest=name, required=subparsers.required)
            for name, subparser in subparsers.sub_parsers.items():
                ap_subparser = ap_subparsers.add_parser(name)
                subparser.apply(ap_subparser)

    def _construct_object_with_parsed(self, parsed: dict[str, Any]) -> T:
        if self.subparsers is not None:
            name, subparsers = self.subparsers

            # optional subparsers will result in `dict[name]` being `None`
            if chosen_subparser := parsed.get(name):
                if chosen_subparser not in subparsers.sub_parsers:
                    raise InvalidParser(f"`{self.shape.__name__}.{name}` was overriden by argument/subparser with same name, got \"{chosen_subparser}\" but should be one of {set(subparsers.sub_parsers.keys())}")
                sub_parser = subparsers.sub_parsers[chosen_subparser]
                parsed[name] = sub_parser._construct_object_with_parsed(parsed)

        # apply argument converters
        for name, argument in self.all_arguments:
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

        return _instantiate_from_dict(self.shape, parsed)


def _instantiate_from_dict[T](cls: type[T], dict_: dict[str, Any]) -> T:
    values = {}
    for _cls in cls.__mro__:
        for name in inspect.get_annotations(_cls, eval_str=True).keys():
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
        for _cls in reversed(cls.__mro__)
        for name, typehint in inspect.get_annotations(_cls, eval_str=True).items()
    }

    # collect declared defaults
    for key, value in {k: v for _cls in cls.__mro__ for k, v in vars(_cls).items()}.items():
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
    # collect arguments and groups
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

    # collect subparsers
    match _collect_subparsers(shape):
        case (name, typehint, partial_subparsers):
            subshapes = partial_subparsers.shapes or extract_subparsers_from_typehint(typehint)
            subparsers_by_name = {
                name: _make_parser(subshape)
                for name, subshape in zip(partial_subparsers.names, subshapes)
            }
            subparsers = (name, Subparsers(subparsers_by_name, required=not union_contains_none(typehint)))
        case _:
            subparsers = None

    return Parser(
        shape,
        arguments,
        list(mx_groups.values()),
        subparsers,
    )


def arcparser[T](shape: type[T]) -> Parser[T]:
    return _make_parser(shape)
