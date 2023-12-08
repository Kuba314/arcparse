from types import NoneType, UnionType
from typing import TYPE_CHECKING, Optional, Union, get_args, get_origin

if TYPE_CHECKING:
    from .parser import ArcParser


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


def extract_subparsers_from_typehint(typehint: type) -> list[type["ArcParser"]] | None:
    origin = get_origin(typehint)
    if origin in {Union, UnionType}:
        return list(get_args(typehint))
    return None


def extract_type_from_typehint(typehint: type) -> type:
    if optional_type := extract_optional_type(typehint):
        return optional_type
    elif collection_type := extract_collection_type(typehint):
        return collection_type
    return typehint
