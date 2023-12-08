from enum import StrEnum, auto
from typing import Any, Optional
import re

import pytest

from arcparse import ArcParser


class Result(StrEnum):
    PASS = auto()
    FAIL = auto()


class Args(ArcParser):
    num: int | None
    result: Result | None
    regex: re.Pattern | None


defaults = {
    "num": None,
    "result": None,
}

@pytest.mark.parametrize(
    "arg_string,provided",
    [
        ("--num 123", {"num": 123}),
        ("--result pass", {"result": Result.PASS}),
        ("--result fail", {"result": Result.FAIL}),
        ("--regex ^\\d+$", {"regex": re.compile(r"^\d+$")}),
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
