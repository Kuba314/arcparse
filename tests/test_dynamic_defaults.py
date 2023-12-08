from typing import Any

import pytest

from arcparse import ArcParser, flag, no_flag, option


class OptArgs(ArcParser):
    optional_str: str | None
    optional_int: int | None
    optional_str_alt: str | None = option()
    default_str: str = "foo"
    default_str_alt: str = option(default="foo")
    default_int: int = 123
    implicit_flag: bool
    explicit_flag: bool = flag()
    no_flag: bool = no_flag()


@pytest.mark.parametrize(
    "defaults,key,value",
    [
        ({"optional_str": "bar"}, "optional_str", "bar"),
        ({"optional_int": 456}, "optional_int", 456),
        ({"optional_str_alt": "bar"}, "optional_str_alt", "bar"),
        ({"default_str": "bar"}, "default_str", "bar"),
        ({"default_str_alt": "bar"}, "default_str_alt", "bar"),
        ({"default_int": 789}, "default_int", 789),
        ({"implicit_flag": True}, "implicit_flag", True),
        ({"implicit_flag": False}, "implicit_flag", False),
        ({"explicit_flag": True}, "explicit_flag", True),
        ({"explicit_flag": False}, "explicit_flag", False),
        ({"no_flag": False}, "no_flag", False),
        ({"no_flag": True}, "no_flag", True),
    ],
)
def test_dynamic_defaults(defaults: dict[str, Any], key: str, value: Any) -> None:
    parsed = OptArgs.parse([], defaults=defaults)

    assert getattr(parsed, key) == value
