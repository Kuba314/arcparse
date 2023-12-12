from typing import Any

import pytest

from arcparse import arcparser, flag, no_flag, option, positional


@arcparser
class OptArgs:
    optional_str: str | None
    optional_int: int | None
    optional_str_alt: str | None = option()
    default_str: str = "foo"
    default_str_alt: str = option(default="foo")
    default_int: int = 123
    implicit_flag: bool
    explicit_flag: bool = flag()
    no_flag: bool = no_flag()


defaults = {
    "optional_str": None,
    "optional_int": None,
    "optional_str_alt": None,
    "default_str": "foo",
    "default_str_alt": "foo",
    "default_int": 123,
    "implicit_flag": False,
    "explicit_flag": False,
    "no_flag": True,
}


def test_defaults_sanity() -> None:
    parsed = OptArgs.parse([])
    for key, value in defaults.items():
        assert getattr(parsed, key) == value


@pytest.mark.parametrize(
    "arg_string,key,value",
    [
        ("--optional-str bar", "optional_str", "bar"),
        ("--optional-int 456", "optional_int", 456),
        ("--optional-str-alt bar", "optional_str_alt", "bar"),
        ("--default-str bar", "default_str", "bar"),
        ("--default-str bar", "default_str", "bar"),
        ("--default-int 789", "default_int", 789),
        ("--implicit-flag", "implicit_flag", True),
        ("--explicit-flag", "explicit_flag", True),
        ("--no-no-flag", "no_flag", False),
    ],
)
def test_defaults(arg_string: str, key: str, value: Any) -> None:
    args = arg_string.split()
    parsed = OptArgs.parse(args)

    for k, v in (defaults | {key: value}).items():
        assert getattr(parsed, k) == v


@arcparser
class PosArgs:
    positional_str: str = positional()
    positional_int: int = positional()
    positional_default_str: str | None = positional()


@pytest.mark.parametrize(
    "arg_string,values",
    [
        ("foo 123", {"positional_str": "foo", "positional_int": 123, "positional_default_str": None}),
        ("foo 123 bar", {"positional_str": "foo", "positional_int": 123, "positional_default_str": "bar"}),
    ],
)
def test_positional_defaults(arg_string: str, values: dict[str, Any]) -> None:
    args = arg_string.split()
    parsed = PosArgs.parse(args)

    for k, v in values.items():
        assert getattr(parsed, k) == v
