from typing import Any

import pytest

from arcparse import arcparser, subparsers


defaults = {key: False for key in ["foo", "bar", "baz"]}


@pytest.mark.parametrize(
    "arg_string,result",
    [
        ("--foo", defaults | {"foo": True}),
        ("--bar", defaults | {"bar": True}),
        ("--baz", defaults | {"baz": True}),
        ("--foo --bar --baz", {"foo": True, "bar": True, "baz": True}),
    ]
)
def test_inheritance(arg_string: str, result: dict[str, str]) -> None:
    class Parent1:
        foo: bool

    class Parent2:
        bar: bool

    @arcparser
    class Argsi(Parent1, Parent2):
        baz: bool

    parsed = Argsi.parse(arg_string.split())
    for k, v in result.items():
        assert getattr(parsed, k) == v


class Common:
    debug: bool

class FooArgs(Common):
    foo: bool

class BarArgs(Common):
    bar: bool


@pytest.mark.parametrize(
    "arg_string,result",
    [
        ("foo --debug --foo", (FooArgs, {"debug": True, "foo": True})),
        ("bar --debug --bar", (BarArgs, {"debug": True, "bar": True})),
    ],
)
def test_inheritance_subparsers(arg_string: str, result: tuple[type, dict[str, Any]]) -> None:
    @arcparser
    class Args:
        action: FooArgs | BarArgs = subparsers("foo", "bar")

    args = Args.parse(arg_string.split())
    type_, value_dict = result
    assert isinstance(action := args.action, type_)
    for k, v in value_dict.items():
        assert getattr(action, k) == v
