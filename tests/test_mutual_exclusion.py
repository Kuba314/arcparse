from typing import Any

import pytest

from arcparse import arcparser, flag, mx_group, option, subparsers, tri_flag
from arcparse.errors import InvalidArgument


def test_group_as_untyped_attribute() -> None:
    @arcparser
    class Args:
        group = mx_group()
        foo: str | None = option(mx_group=group)
        bar: str | None = option(mx_group=group)

    Args.parse([])


def test_group_elements_both_nonoptional() -> None:
    class Args:
        foo: str = option(mx_group=(group := mx_group()))
        bar: str = option(mx_group=group)

    with pytest.raises(InvalidArgument):
        arcparser(Args)


def test_group_elements_some_nonoptional() -> None:
    class Args:
        foo: str = option(mx_group=(group := mx_group()))
        bar: str | None = option(mx_group=group)

    with pytest.raises(InvalidArgument):
        arcparser(Args)


@arcparser
class Args:
    foo: str | None = option(mx_group=(option_group := mx_group()))
    bar: str | None = option(mx_group=option_group)

    flag1: bool = flag(mx_group=(flag_group := mx_group()))
    flag2: bool = flag(mx_group=flag_group)


@pytest.mark.parametrize(
    "string,result",
    [
        ("--foo foo", {"foo": "foo", "bar": None, "flag1": False, "flag2": False}),
        ("--bar bar", {"foo": None, "bar": "bar", "flag1": False, "flag2": False}),
        ("--flag1", {"foo": None, "bar": None, "flag1": True, "flag2": False}),
        ("--flag2", {"foo": None, "bar": None, "flag1": False, "flag2": True}),
        ("--foo foo --flag1", {"foo": "foo", "bar": None, "flag1": True, "flag2": False}),
        ("--foo foo --flag2", {"foo": "foo", "bar": None, "flag1": False, "flag2": True}),
        ("--bar bar --flag1", {"foo": None, "bar": "bar", "flag1": True, "flag2": False}),
        ("--bar bar --flag2", {"foo": None, "bar": "bar", "flag1": False, "flag2": True}),
        ("--foo foo --bar bar", None),
        ("--flag1 --flag2", None),
    ],
)
def test_mutual_exclusion_valid(string: str, result: dict[str, Any]) -> None:
    if result is None:
        with pytest.raises(SystemExit):
            Args.parse(string.split())
    else:
        args = Args.parse(string.split())
        for k, v in result.items():
            assert getattr(args, k) == v


def test_mutual_exclusion_required() -> None:
    @arcparser
    class Args:
        foo: str | None = option(mx_group=(option_group := mx_group(required=True)))
        bar: str | None = option(mx_group=option_group)

    with pytest.raises(SystemExit):
        Args.parse("".split())

    parsed = Args.parse("--foo foo".split())
    assert parsed.foo == "foo"
    assert parsed.bar is None

    parsed = Args.parse("--bar bar".split())
    assert parsed.foo is None
    assert parsed.bar == "bar"

    with pytest.raises(SystemExit):
        Args.parse("--foo foo --bar bar".split())


def test_tri_flag_inside_mx_group() -> None:
    @arcparser
    class Args:
        foo: str | None = option(mx_group=(group := mx_group()))
        bar: bool | None = tri_flag(mx_group=group)

    parsed = Args.parse("".split())
    assert parsed.foo is None
    assert parsed.bar is None

    parsed = Args.parse("--foo foo".split())
    assert parsed.foo == "foo"
    assert parsed.bar is None

    parsed = Args.parse("--bar".split())
    assert parsed.foo is None
    assert parsed.bar is True

    parsed = Args.parse("--no-bar".split())
    assert parsed.foo is None
    assert parsed.bar is False

    with pytest.raises(SystemExit):
        Args.parse("--foo foo --bar".split())

    with pytest.raises(SystemExit):
        Args.parse("--foo foo --no-bar".split())


def test_tri_flag_inside_subparser() -> None:
    class FooArgs:
        foo: str

    class BarArgs:
        bar: bool | None

    @arcparser
    class Args:
        foo_bar: FooArgs | BarArgs = subparsers("foo", "bar")

    parsed = Args.parse("bar".split())
    assert isinstance(foo_bar := parsed.foo_bar, BarArgs)
    assert foo_bar.bar is None

    parsed = Args.parse("bar --bar".split())
    assert isinstance(foo_bar := parsed.foo_bar, BarArgs)
    assert foo_bar.bar is True

    parsed = Args.parse("bar --no-bar".split())
    assert isinstance(foo_bar := parsed.foo_bar, BarArgs)
    assert foo_bar.bar is False

    with pytest.raises(SystemExit):
        Args.parse("bar --bar --no-bar".split())
