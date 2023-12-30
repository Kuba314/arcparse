from enum import StrEnum, auto
from typing import Any, Literal
import re

import pytest

from arcparse import arcparser, option, positional


class Result(StrEnum):
    PASS = auto()
    FAIL = auto()


@arcparser
class Args:
    num: int | None
    num_default: int = option(default="123")
    result: Result | None
    regex: re.Pattern | None
    literal: Literal["yes", "no"] | None


defaults = {
    "num": None,
    "num_default": 123,
    "result": None,
    "regex": None,
    "literal": None,
}

@pytest.mark.parametrize(
    "arg_string,provided",
    [
        ("--num 123", {"num": 123}),
        ("--num-default 456", {"num_default": 456}),
        ("--result pass", {"result": Result.PASS}),
        ("--result fail", {"result": Result.FAIL}),
        ("--regex ^\\d+$", {"regex": re.compile(r"^\d+$")}),
        ("--literal yes", {"literal": "yes"}),
        ("--literal no", {"literal": "no"}),
    ]
)
def test_auto_converter_valid(arg_string: str, provided: dict[str, Any]) -> None:
    parsed = Args.parse(arg_string.split())

    for k, v in (defaults | provided).items():
        assert getattr(parsed, k) == v


@pytest.mark.parametrize(
    "arg_string",
    [
        "--num foo",
        "--result bar",
        "--regex '('"
    ]
)
def test_option_invalid(arg_string: str) -> None:
    with pytest.raises(BaseException):
        Args.parse(args = arg_string.split())


def test_enum_positional() -> None:
    @arcparser
    class Args:
        result: Result = positional()

    parsed = Args.parse("pass".split())
    assert parsed.result == Result.PASS

    parsed = Args.parse("fail".split())
    assert parsed.result == Result.FAIL


def test_literal_positional() -> None:
    @arcparser
    class Args:
        literal: Literal["yes", "no"] = positional()

    parsed = Args.parse("yes".split())
    assert parsed.literal == "yes"

    parsed = Args.parse("no".split())
    assert parsed.literal == "no"
