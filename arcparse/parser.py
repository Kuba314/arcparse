from argparse import ArgumentParser
from dataclasses import make_dataclass
from enum import StrEnum
from types import NoneType, UnionType
from typing import Any, Optional, Self, Union, get_args, get_origin

from .argument import _Option, _BaseValueArgument, _Flag, _Positional, Argument, void



def _extract_optional_type(typehint: type) -> type | None:
    origin = get_origin(typehint)
    if origin == Optional:
        return get_args(typehint)[0]
    elif origin in {Union, UnionType}:
        args = get_args(typehint)
        if len(args) == 2 and args[1] == NoneType:
            return args[0]
    return None


def _extract_collection_type(typehint: type) -> type | None:
    origin = get_origin(typehint)
    if origin == list:
        return get_args(typehint)[0]
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
        raise Exception(f"Could not parse bool from \"{value}\"")


class ArcParser:
    @classmethod
    def parse(cls, defaults: dict[str, Any] = {}) -> Self:
        # collect declared typehints
        all_params: dict[str, tuple[type, Any]] = {name: (typehint, void) for name, typehint in cls.__annotations__.items()}

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
        arguments: dict[str, Argument] = {}
        for name, (typehint, default) in all_params.items():
            if isinstance(default, Argument):
                # already an argument
                argument = default
            else:
                typ = _extract_type_from_typehint(typehint)

                if typ is bool:
                    argument = _Flag(default=default)
                elif isinstance(typ, StrEnum):
                    argument = _Option(default=default, choices=list(typ), converter=typ)
                else:
                    argument = _Option(default=default, converter=typ if typ is not str else None)
            argument.name = name
            arguments[name] = argument

        # apply additional defaults to arguments
        for name, default in defaults.items():
            if name not in arguments:
                raise Exception("Unknown param provided")

            arg = arguments[name]

            typehint, _ = all_params[name]
            desired_type = _extract_type_from_typehint(typehint)
            if desired_type is bool:
                if not isinstance(arg, _Flag):
                    raise Exception("Flag argument expected for bool types")
                arg.default = _to_bool(default)
            else:
                if not isinstance(arg, _BaseValueArgument):
                    raise Exception("Non-flag argument type expected for non-bool types")
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

            typehint, _ = all_params[name]
            type_ = _extract_type_from_typehint(typehint)
            if type_ is not str:
                arg.converter = type_

        # update `multiple`
        for name, arg in arguments.items():
            if not isinstance(arg, _BaseValueArgument):
                continue

            typehint, _ = all_params[name]
            if _extract_collection_type(typehint):
                arg.multiple = True

        # update `required` and `optional`
        for name, arg in arguments.items():
            if isinstance(arg, _Option):
                typehint, _ = all_params[name]
                is_optional = bool(_extract_optional_type(typehint))
                is_collection = bool(_extract_collection_type(typehint))
                if not is_optional and not is_collection and arg.default is void:
                    arg.required = True
            elif isinstance(arg, _Positional):
                typehint, _ = all_params[name]
                is_optional = bool(_extract_optional_type(typehint))
                is_collection = bool(_extract_collection_type(typehint))
                if is_optional or is_collection or arg.default is not void:
                    arg.required = False

        parser = ArgumentParser()
        for arg in arguments.values():
            arg.register(parser)

        args = parser.parse_args()

        # create a temporary dataclass to shove parsed args into
        dto_cls = make_dataclass(cls.__name__, fields={(name, typ) for name, (typ, _) in all_params.items()})
        return dto_cls(**args.__dict__)
