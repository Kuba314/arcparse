from typing import Any

import pytest

from arcparse import arcparser, flag, no_flag, tri_flag


@arcparser
class Args:
    foo: bool
    bar: bool = no_flag()
    barr: bool = no_flag("-B")
    barrr: bool = no_flag("-R", short_only=True)
    baz: bool = flag(short="-z")
    boo: bool = flag(short="-o", short_only=True)
    c: bool = flag(short_only=True)


defaults = {
    "foo": False,
    "bar": True,
    "barr": True,
    "barrr": True,
    "baz": False,
    "boo": False,
    "c": False,
}


@pytest.mark.parametrize(
    "arg_string,provided",
    [
        ("--foo", {"foo": True}),
        ("--no-bar", {"bar": False}),
        ("--no-barr", {"barr": False}),
        ("-B", {"barr": False}),
        ("-R", {"barrr": False}),
        ("--baz", {"baz": True}),
        ("-z", {"baz": True}),
        ("-o", {"boo": True}),
        ("-c", {"c": True}),
    ]
)
def test_flag_valid(arg_string: str, provided: dict[str, Any]) -> None:
    parsed = Args.parse(arg_string.split())

    for k, v in (defaults | provided).items():
        assert getattr(parsed, k) == v


@pytest.mark.parametrize(
    "arg_string",
    [
        "--bar",
        "--barr",
        "--no-barrr",
        "--no-foo",
        "--boo",
    ]
)
def test_flag_invalid(arg_string: str) -> None:
    with pytest.raises(SystemExit):
        Args.parse(args = arg_string.split())



@pytest.mark.parametrize(
    "string,result",
    [
        ("", {"foo": None, "bar": None}),
        ("--foo", {"foo": True, "bar": None}),
        ("--no-foo", {"foo": False, "bar": None}),
        ("--foo --no-foo", None),
        ("", {"foo": None, "bar": None}),
        ("--bar", {"foo": None, "bar": True}),
        ("--no-bar", {"foo": None, "bar": False}),
        ("--bar --no-bar", None),
    ],
)
def test_tri_flag(string: str, result: dict[str, Any]):
    @arcparser
    class Args:
        foo: bool | None
        bar: bool | None = tri_flag()

    if result is None:
        with pytest.raises(SystemExit):
            Args.parse(string.split())
    else:
        args = Args.parse(string.split())
        for k, v in result.items():
            assert getattr(args, k) == v
