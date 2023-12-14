from typing import Any

import pytest

from arcparse import MxGroup, arcparser, flag, option
from arcparse.errors import InvalidArgument


def test_group_as_untyped_attribute() -> None:
    @arcparser
    class Args:
        group = MxGroup()
        foo: str | None = option(mx_group=group)
        bar: str | None = option(mx_group=group)

    Args.parse([])


def test_group_elements_both_nonoptional() -> None:
    class Args:
        foo: str = option(mx_group=(group := MxGroup()))
        bar: str = option(mx_group=group)

    with pytest.raises(InvalidArgument):
        arcparser(Args)


def test_group_elements_some_nonoptional() -> None:
    class Args:
        foo: str = option(mx_group=(group := MxGroup()))
        bar: str | None = option(mx_group=group)

    with pytest.raises(InvalidArgument):
        arcparser(Args)


@arcparser
class Args:
    foo: str | None = option(mx_group=(option_group := MxGroup()))
    bar: str | None = option(mx_group=option_group)

    flag1: bool = flag(mx_group=(flag_group := MxGroup()))
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
