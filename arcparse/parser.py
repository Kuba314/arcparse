from __future__ import annotations
from argparse import ArgumentParser
from dataclasses import make_dataclass
from enum import StrEnum
from types import NoneType, UnionType
from typing import Any, Optional, Self, Union, get_args, get_origin
import inspect

from .argument import _Option, _BaseValueArgument, _Flag, _Positional, _BaseArgument, void
from .subparser import _Subparsers


def _extract_optional_type(typehint: type) -> type | None:
    origin = get_origin(typehint)
    if origin == Optional:
        return get_args(typehint)[0]
    elif origin in {Union, UnionType}:
        args = get_args(typehint)
        if len(args) == 2:
            if args[0] == NoneType:
                return args[1]
            elif args[1] == NoneType:
                return args[0]
    return None


def _extract_collection_type(typehint: type) -> type | None:
    origin = get_origin(typehint)
    if origin == list:
        return get_args(typehint)[0]
    return None


def _extract_subparsers_from_typehint(typehint: type) -> list[type[ArcParser]] | None:
    origin = get_origin(typehint)
    if origin in {Union, UnionType}:
        return list(get_args(typehint))
    return None


def _extract_type_from_typehint(typehint: type) -> type:
    if optional_type := _extract_optional_type(typehint):
        return optional_type
    elif collection_type := _extract_collection_type(typehint):
        return collection_type
    return typehint


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
    def parse(cls, args: list[str] | None = None, defaults: dict[str, Any] = {}) -> Self:
        parser = ArgumentParser()
        cls._apply(parser, defaults=defaults)
        parsed = parser.parse_args(args)

        return cls.from_dict(parsed.__dict__)

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
    def _apply(cls, parser: ArgumentParser, defaults: dict[str, Any] = {}) -> None:
        typehints, arguments = cls.__collect_arguments()

        # apply additional defaults to arguments
        for name, default in defaults.items():
            if name not in arguments:
                raise Exception("Unknown param provided")

            arg = arguments[name]

            typehint = typehints[name]
            desired_type = _extract_type_from_typehint(typehint)
            if desired_type is bool:
                if not isinstance(arg, _Flag):
                    raise Exception("Flag argument expected for bool types")
                arg.default = _to_bool(default)
            else:
                if not isinstance(arg, _BaseValueArgument):
                    raise Exception(
                        "Non-flag argument type expected for non-bool types"
                    )
                converter = arg.converter
                if converter is None:
                    converter = desired_type

                if not isinstance(default, desired_type):
                    default = converter(default)
                arg.default = default

        # update `converter` if not set
        for name, arg in arguments.items():
            if not isinstance(arg, _BaseValueArgument):
                continue

            if arg.converter is not None:
                continue

            type_ = _extract_type_from_typehint(typehints[name])
            if type_ is not str:
                arg.converter = type_

        # update `multiple`
        for name, arg in arguments.items():
            if not isinstance(arg, _BaseValueArgument):
                continue

            if _extract_collection_type(typehints[name]):
                arg.multiple = True

        # update `required` and `optional`
        for name, arg in arguments.items():
            if isinstance(arg, _Option):
                typehint = typehints[name]
                is_optional = bool(_extract_optional_type(typehint))
                is_collection = bool(_extract_collection_type(typehint))
                if not is_optional and not is_collection and arg.default is void:
                    arg.required = True
            elif isinstance(arg, _Positional):
                typehint = typehints[name]
                is_optional = bool(_extract_optional_type(typehint))
                is_collection = bool(_extract_collection_type(typehint))
                if is_optional or is_collection or arg.default is not void:
                    arg.required = False

        for name, arg in arguments.items():
            arg.apply(parser, name)

        if subparsers_triple := cls.__collect_subparsers():
            name, subparsers, subparser_types = subparsers_triple
            subparsers.apply(parser, name, subparser_types, defaults=defaults)

    @classmethod
    def __collect_subparsers(cls) -> tuple[str, _Subparsers, list[type[ArcParser]]] | None:
        subparsers = [(key, value) for key, value in vars(cls).items() if isinstance(value, _Subparsers)]
        match subparsers:
            case []:
                return None
            case [(name, value)]:
                typehint = inspect.get_annotations(cls, eval_str=True)[name]
                if not (subparser_types := _extract_subparsers_from_typehint(typehint)):
                    raise Exception(f"Unable to extract subparser types from {typehint}, expected a non-empty union of ArcParser types")
                return name, value, subparser_types
            case _:
                raise Exception(f"Multiple subparsers definitions found on {cls}")

    @classmethod
    def __collect_arguments(cls) -> tuple[dict[str, type], dict[str, _BaseArgument]]:
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

            if key not in all_params:
                raise Exception(f"Argument {key} is missing a type-hint")

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

            if isinstance(default, _BaseValueArgument) and _extract_type_from_typehint(typehint) == bool:
                raise Exception("Unable to make type=bool, everything would be True")
            elif isinstance(default, _BaseArgument):
                argument = default
            else:
                typ = _extract_type_from_typehint(typehint)

                if typ is bool:
                    if _extract_optional_type(typehint):
                        raise Exception("Unable to make type=bool, everything would be True")
                    argument = _Flag(default=default)
                elif isinstance(typ, StrEnum):
                    argument = _Option(default=default, choices=list(typ), converter=typ)
                else:
                    argument = _Option(default=default, converter=typ if typ is not str else None)
            arguments[name] = argument

        return (
            {name: typehint for name, (typehint, _) in all_params.items()},
            arguments,
        )
