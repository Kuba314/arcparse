from types import NoneType
from typing import Any

import pytest

from arcparse import arcparser, positional, subparsers


class FooArgs:
    arg1: str

class BarArgs:
    arg2: int = positional()

@arcparser
class ReqArgs:
    action: FooArgs | BarArgs = subparsers("foo", "bar")

@arcparser
class OptArgs:
    action: FooArgs | BarArgs | None = subparsers("foo", "bar")


@pytest.mark.parametrize(
    "string,result",
    [
        ("", None),
        ("foo --arg1 foo", (FooArgs, {"arg1": "foo"})),
        ("bar 123", (BarArgs, {"arg2": 123})),
        ("bar bar", None),
    ],
)
def test_subparsers_required(string: str, result: tuple[type, dict[str, Any]] | None) -> None:
    if result is None:
        with pytest.raises(SystemExit):
            ReqArgs.parse(string.split())
    else:
        args = ReqArgs.parse(string.split())
        type_, value_dict = result
        assert isinstance(action := args.action, type_)
        for k, v in value_dict.items():
            assert getattr(action, k) == v


@pytest.mark.parametrize(
    "string,result",
    [
        ("", (NoneType, None)),
        ("foo --arg1 foo", (FooArgs, {"arg1": "foo"})),
        ("bar 123", (BarArgs, {"arg2": 123})),
        ("bar bar", None),
    ],
)
def test_subparsers_optional(string: str, result: tuple[type, dict[str, Any] | None] | None) -> None:
    if result is None:
        with pytest.raises(SystemExit):
            OptArgs.parse(string.split())
    else:
        args = OptArgs.parse(string.split())
        type_, value_dict = result
        assert isinstance(action := args.action, type_)
        if value_dict is None:
            assert action is None
        else:
            for k, v in value_dict.items():
                assert getattr(action, k) == v
