from typing import Any

import pytest

from arcparse import arcparser, positional


@arcparser
class Args:
    foo: str = positional()
    bar: str | None = positional()
    baz: str = positional(default="123")


defaults = {
    "bar": None,
    "baz": "123",
}


@pytest.mark.parametrize(
    "arg_string,provided",
    [
        ("A", {"foo": "A"}),
        ("A B", {"foo": "A", "bar": "B"}),
        ("A B C", {"foo": "A", "bar": "B", "baz": "C"}),
    ],
)
def test_positional_valid(arg_string: str, provided: dict[str, Any]) -> None:
    parsed = Args.parse(arg_string.split())

    for k, v in (defaults | provided).items():
        assert getattr(parsed, k) == v


@pytest.mark.parametrize(
    "arg_string",
    [
        "",
        "A B C D",
    ],
)
def test_positional_invalid(arg_string: str) -> None:
    with pytest.raises(SystemExit):
        Args.parse(args=arg_string.split())
