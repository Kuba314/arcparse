from typing import Any
import pytest
from arcparse import ArcParser, positional, flag, no_flag, subparsers


class ReqArgs(ArcParser):
    positional_int: int = positional()


class AllArgs(ArcParser):
    optional_str: str | None
    optional_int: int | None
    default_str: str = "foo"
    default_int: int = 123
    implicit_flag: bool
    explicit_flag: bool = flag()
    no_flag: bool = no_flag()

    action: ReqArgs | None = subparsers("")


defaults = {
    "optional_str": None,
    "optional_int": None,
    "default_str": "foo",
    "default_int": 123,
    "implicit_flag": False,
    "explicit_flag": False,
    "no_flag": True,
}


def test_defaults_sanity() -> None:
    parsed = AllArgs.parse([])
    for key, value in defaults.items():
        assert getattr(parsed, key) == value


@pytest.mark.parametrize(
    "arg_string,key,value",
    [
        ("--optional-str bar", "optional_str", "bar"),
        ("--optional-int 456", "optional_int", 456),
        ("--default-str baz", "default_str", "baz"),
        ("--default-int 789", "default_int", 789),
        ("--implicit-flag", "implicit_flag", True),
        ("--explicit-flag", "explicit_flag", True),
        ("--no-no-flag", "no_flag", False),
    ],
)
def test_defaults(arg_string: str, key: str, value: Any) -> None:
    args = arg_string.split()
    parsed = AllArgs.parse(args)

    for k, v in (defaults | {key: value}).items():
        assert getattr(parsed, k) == v
