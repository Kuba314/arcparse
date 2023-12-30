from types import NoneType
from typing import Any

import pytest

from arcparse import arcparser, positional, subparsers
from arcparse.errors import InvalidParser


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
        ("", SystemExit),
        ("foo --arg1 foo", (FooArgs, {"arg1": "foo"})),
        ("bar 123", (BarArgs, {"arg2": 123})),
        ("bar bar", ValueError),
    ],
)
def test_subparsers_required(string: str, result: tuple[type, dict[str, Any]] | type[BaseException]) -> None:
    if isinstance(result, type):
        with pytest.raises(result):
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
        ("bar bar", ValueError),
    ],
)
def test_subparsers_optional(string: str, result: tuple[type, dict[str, Any] | None] | type[BaseException]) -> None:
    if isinstance(result, type):
        with pytest.raises(result):
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


def test_only_one_subparsers() -> None:
    class Foo:
        foo: str

    class Bar:
        bar: str

    class Baz:
        baz: str

    class Boo:
        boo: str

    class Args:
        foo_or_bar: Foo | Bar = subparsers("foo", "bar")
        baz_or_boo: Baz | Boo = subparsers("baz", "boo")

    with pytest.raises(InvalidParser):
        arcparser(Args)
