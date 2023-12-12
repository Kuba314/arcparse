from enum import StrEnum, auto

import pytest

from arcparse import arcparser, itemwise, option
from arcparse.converters import csv


def test_itemwise() -> None:
    class Result(StrEnum):
        PASS = auto()
        FAIL = auto()

        @classmethod
        def from_int(cls, arg: str) -> "Result":
            number = int(arg)
            return cls.PASS if number == 1 else cls.FAIL

    # @arcparser
    class Xd:
        results: list[Result] = option(converter=itemwise(Result.from_int))
    Args = arcparser(Xd)
    args = Args.parse("--results 0 1 0".split())
    assert isinstance(args.results, list)
    assert len(args.results) == 3
    assert args.results[0] == Result.FAIL
    assert args.results[1] == Result.PASS
    assert args.results[2] == Result.FAIL


@pytest.mark.parametrize(
    "string,attr,expected",
    [
        ("--strings foo,bar,baz", "strings", ["foo", "bar", "baz"]),
        ("--ints 123,456,789", "ints", [123, 456, 789]),
    ],
)
def test_csv(string: str, attr: str, expected: list[str]) -> None:
    @arcparser
    class Args:
        strings: list[str] = option(converter=csv())
        ints: list[int] = option(converter=csv(int))

    args = Args.parse(string.split())
    assert getattr(args, attr) == expected
