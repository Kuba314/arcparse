import pytest

from arcparse import ArcParser, option
from arcparse.converters import csv


@pytest.mark.parametrize(
    "string,attr,expected",
    [
        ("--strings foo,bar,baz", "strings", ["foo", "bar", "baz"]),
        ("--ints 123,456,789", "ints", [123, 456, 789]),
    ],
)
def test_csv(string: str, attr: str, expected: list[str]) -> None:
    class Args(ArcParser):
        strings: list[str] = option(converter=csv())
        ints: list[int] = option(converter=csv(int))

    args = Args.parse(string.split())
    assert getattr(args, attr) == expected
