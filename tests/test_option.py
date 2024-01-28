from typing import Any, Optional

import pytest

from arcparse import arcparser, option


@arcparser
class Args:
    foo: str = option("-f")
    bar: None | str
    baz: str = option("-z", short_only=True, default="123")
    boo: Optional[str]
    c: str = option(short_only=True, default="123")


defaults = {
    "bar": None,
    "baz": "123",
    "boo": None,
    "c": "123",
}


@pytest.mark.parametrize(
    "arg_string,provided",
    [
        ("--foo A", {"foo": "A"}),
        ("-f A", {"foo": "A"}),
        ("--foo A --bar B", {"foo": "A", "bar": "B"}),
        ("--foo A --bar B -z C", {"foo": "A", "bar": "B", "baz": "C"}),
        ("--foo A -z C --boo D", {"foo": "A", "baz": "C", "boo": "D"}),
        ("--foo A -c B", {"foo": "A", "c": "B"}),
    ]
)
def test_option_valid(arg_string: str, provided: dict[str, Any]) -> None:
    parsed = Args.parse(arg_string.split())

    for k, v in (defaults | provided).items():
        assert getattr(parsed, k) == v


@pytest.mark.parametrize(
    "arg_string",
    [
        "--foo foo --bar bar --baz baz",
        "--bar bar",
    ]
)
def test_option_invalid(arg_string: str) -> None:
    with pytest.raises(SystemExit):
        Args.parse(args = arg_string.split())
