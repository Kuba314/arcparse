from enum import StrEnum, auto
from typing import Optional
import pytest

from arcparse import ArcParser, positional, option, flag, no_flag, subparsers


class Pos(ArcParser):
    foo: str = positional()
    bar: str | None = positional()
    baz: str = positional(default="123")


class Opt(ArcParser):
    foo: str
    bar: None | str
    baz: str = option("-b", short_only=True, default="123")
    boo: Optional[str]


class Flag(ArcParser):
    foo: bool
    bar: bool = no_flag()
    baz: bool = flag(short="-z")
    boo: bool = flag(short="-o", short_only=True)


class Conv(ArcParser):
    class Result(StrEnum):
        PASS = auto()
        FAIL = auto()

    num: int | None
    res: Result | None


class Args(ArcParser):
    sub: Pos | Opt | Flag | Conv = subparsers("pos", "opt", "flag", "conv")


@pytest.mark.parametrize(
    "arg_string,should_throw",
    [
        ("", True),
        ("pos 1", False),
        ("pos 1 2", False),
        ("pos 1 2 3", False),
        ("pos", True),
        ("pos 1 2 3 4", True),

        ("opt --foo foo --bar bar -b baz", False),
        ("opt --foo foo --bar bar --baz baz", True),
        ("opt --foo foo --bar bar", False),
        ("opt --foo foo", False),
        ("opt --bar bar", True),

        ("flag --foo", False),
        ("flag --no-bar", False),
        ("flag --bar", True),
        ("flag --no-foo", True),
        ("flag --baz", False),
        ("flag -z", False),
        ("flag -o", False),
        ("flag --boo", True),

        ("conv --num 123", False),
        ("conv --num foo", True),
        ("conv --res pass", False),
        ("conv --res fail", False),
        ("conv --res bar", True),
    ]
)
def test_valid(arg_string: str, should_throw: bool) -> None:
    args = arg_string.split()

    if should_throw:
        with pytest.raises(SystemExit):
            Args.parse(args)
    else:
        Args.parse(args)
