from typing import Any
import pytest

from arcparse import ArcParser, flag, no_flag


class Args(ArcParser):
    foo: bool
    bar: bool = no_flag()
    baz: bool = flag(short="-z")
    boo: bool = flag(short="-o", short_only=True)


defaults = {
    "foo": False,
    "bar": True,
    "baz": False,
    "boo": False,
}


@pytest.mark.parametrize(
    "arg_string,provided",
    [
        ("--foo", {"foo": True}),
        ("--no-bar", {"bar": False}),
        ("--baz", {"baz": True}),
        ("-z", {"baz": True}),
        ("-o", {"boo": True}),
    ]
)
def test_option_valid(arg_string: str, provided: dict[str, Any]) -> None:
    parsed = Args.parse(arg_string.split())

    for k, v in (defaults | provided).items():
        assert getattr(parsed, k) == v


@pytest.mark.parametrize(
    "arg_string",
    [
        "flag --bar",
        "flag --no-foo",
        "flag --boo",
    ]
)
def test_option_invalid(arg_string: str) -> None:
    with pytest.raises(SystemExit):
        Args.parse(args = arg_string.split())
