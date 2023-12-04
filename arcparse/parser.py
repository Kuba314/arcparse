from __future__ import annotations
from argparse import ArgumentParser
from dataclasses import make_dataclass
from collections.abc import Sequence
from enum import StrEnum
from types import NoneType, UnionType
from typing import Any, Self, Union, get_args, get_origin
import inspect
import re

from .arguments import _Option, _BaseValueArgument, _Flag, _BaseArgument, _ValueOverride, void
from .converters import itemwise
from .subparser import _Subparsers
from .typehints import extract_collection_type, extract_subparsers_from_typehint, extract_type_from_typehint
from .converters import itemwise


def _to_bool(value: str) -> bool:
    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        raise Exception(f'Could not parse bool from "{value}"')


class _InstanceCheckMeta(type):
    """Only check whether class-name is equal in isinstance()"""
    def __instancecheck__(self, __instance: Any) -> bool:
        return self.__name__ == __instance.__class__.__name__


class ArcParser(metaclass=_InstanceCheckMeta):
    """Use _InstanceCheckMeta to allow for type-narrowing of subparser objects"""
    @classmethod
    def parse(cls, args: Sequence[str] | None = None, defaults: dict[str, Any] = {}) -> Self:
        parser = ArgumentParser()
        already_resolved = cls._apply(parser, defaults=defaults)
        parsed = parser.parse_args(args)

        return cls.from_dict(already_resolved | parsed.__dict__)

    @classmethod
    def from_dict(cls, dict: dict[str, Any]) -> Self:
        values = {}
        if subparsers_triple := cls.__collect_subparsers():
            name, subparsers, subparser_types = subparsers_triple

            # optional subparsers will result in `dict[name]` being `None`
            if chosen_subparser := dict[name]:
                subparser_type = subparser_types[subparsers.names.index(chosen_subparser)]
                values[name] = subparser_type.from_dict(dict)

        annotations = inspect.get_annotations(cls, eval_str=True)
        for name in annotations.keys():
            # skip already added subparser result
            if name in values:
                continue

            values[name] = dict.pop(name)

        dto_cls = make_dataclass(cls.__name__, fields=annotations)
        def instancecheck(inst) -> bool:
            return cls.__name__ == inst.__class__.__name__
        dto_cls.__instancecheck__ = instancecheck.__get__(cls, type)
        return dto_cls(**values)

    @classmethod
    def _apply(cls, parser: ArgumentParser, defaults: dict[str, Any] = {}) -> dict[str, Any]:
        """Apply arguments and defaults to ArgumentParser returning already resolved values"""
        arguments = cls.__collect_arguments()

        cls.__apply_argument_defaults(arguments, defaults)

        for name, arg in arguments.items():
            arg.apply(parser, name)

        if subparsers_triple := cls.__collect_subparsers():
            name, subparsers, subparser_types = subparsers_triple
            subparsers.apply(parser, name, subparser_types, defaults=defaults)

        return {
            name: arg.value_override
            for name, arg in arguments.items()
            if isinstance(arg, _ValueOverride) and arg.value_override is not void
        }


    @classmethod
    def __collect_arguments(cls) -> dict[str, _BaseArgument]:
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

            # ignore untyped class variables
            if key not in all_params:
                if isinstance(value, _BaseArgument):
                    raise Exception(f"Argument {key} is missing a type-hint and would be ignored")
                continue

            typehint, _ = all_params[key]
            all_params[key] = (typehint, value)

        # construct arguments
        arguments: dict[str, _BaseArgument] = {}
        for name, (typehint, default) in all_params.items():
            if isinstance(default, _Subparsers):
                continue

            if get_origin(typehint) in {Union, UnionType}:
                union_args = get_args(typehint)
                if len(union_args) > 2 or NoneType not in union_args:
                    raise Exception("Union can be used only for optional arguments (length of 2, 1 of them being None)")

            if isinstance(default, _BaseArgument):
                argument = default
            else:
                argument = cls.__construct_argument(typehint, default)

            argument.resolve_with_typehint(typehint)
            arguments[name] = argument

        return arguments

    @classmethod
    def __collect_subparsers(cls) -> tuple[str, _Subparsers, list[type[ArcParser]]] | None:
        subparsers = [(key, value) for key, value in vars(cls).items() if isinstance(value, _Subparsers)]
        match subparsers:
            case []:
                return None
            case [(name, value)]:
                if not (typehint := inspect.get_annotations(cls, eval_str=True)[name]):
                    raise Exception("subparsers have to be type-hinted")
                if not (subparser_types := extract_subparsers_from_typehint(typehint)):
                    raise Exception(f"Unable to extract subparser types from {typehint}, expected a non-empty union of ArcParser types")
                return name, value, subparser_types
            case _:
                raise Exception(f"Multiple subparsers definitions found on {cls}")

    @staticmethod
    def __construct_argument(typehint: type, default: Any) -> _BaseArgument:
        if typehint is bool:
            if default is not void:
                raise Exception(f"defaults don't make sense for flags")
            return _Flag()

        actual_type = extract_type_from_typehint(typehint)
        if actual_type is bool:
            raise Exception(f"Can't construct argument with inner type bool, conversion would be always True")
        elif getattr(actual_type, "_is_protocol", False):
            raise Exception("Argument with no converter can't be typed as a Protocol subclass")

        if type_ := extract_collection_type(typehint):
            converter = itemwise(type_)
        else:
            converter = actual_type

        if issubclass(actual_type, StrEnum):
            return _Option(default=default, choices=list(actual_type), converter=converter)
        elif actual_type == re.Pattern:
            return _Option(default=default, converter=re.compile)

        return _Option(default=default, converter=converter if actual_type is not str else None)

    @staticmethod
    def __apply_argument_defaults(arguments: dict[str, _BaseArgument], defaults: dict[str, Any]) -> None:
        for name, default in defaults.items():
            if name not in arguments:
                raise Exception("Unknown param provided")

            arg = arguments[name]
            if isinstance(arg, _ValueOverride):
                arg.value_override = default
                continue

            if not isinstance(arg, _BaseValueArgument):
                raise Exception(f"Argument \"{name}\" is not a value argument, can't set its default")

            desired_type = extract_type_from_typehint(arg.typehint)
            if desired_type is bool:
                arg.default = _to_bool(default)
            else:
                converter = arg.converter or desired_type

                # only check whether the default is the correct type when the type supports isinstance checks
                is_runtime_checkable = not getattr(desired_type, "_is_protocol", False) or getattr(desired_type, "_is_runtime_protocol", False)
                if is_runtime_checkable and not isinstance(default, desired_type):
                    default = converter(default)
                arg.default = default
