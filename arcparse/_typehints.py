from types import NoneType, UnionType
from typing import Literal, Optional, Union, get_args, get_origin

from arcparse.errors import InvalidTypehint


def extract_optional_type(typehint: type) -> type | None:
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


def extract_collection_type(typehint: type) -> type | None:
    origin = get_origin(typehint)
    if origin == list:
        return get_args(typehint)[0]
    return None


def extract_subparsers_from_typehint(typehint: type) -> list[type]:
    origin = get_origin(typehint)
    if origin in {Union, UnionType}:
        return list(get_args(typehint))
    raise InvalidTypehint(f"Unable to extract subparser types from {typehint}, expected a non-empty union of ArcParser types")


def extract_type_from_typehint(typehint: type) -> type:
    if optional_type := extract_optional_type(typehint):
        return optional_type
    elif collection_type := extract_collection_type(typehint):
        return collection_type
    return typehint


def extract_literal_strings(typehint: type) -> list[str] | None:
    origin = get_origin(typehint)
    if origin != Literal:
        return None

    args = get_args(typehint)
    if not all(isinstance(arg, str) for arg in args):
        return None

    return list(args)


def union_contains_none(typehint: type) -> bool:
    return get_origin(typehint) in {Union, UnionType} and NoneType in get_args(typehint)
