from typing import cast

import pytest

from arcparse import arcparser, option
from arcparse.arguments import Option
from arcparse.parser import Parser


def test_override_make_optional() -> None:
    class BaseArgs:
        foo: str = option()

    @arcparser
    class Args(BaseArgs):
        @staticmethod
        def __post_init__(parser: Parser) -> None:
            option = cast(Option, parser.arguments["foo"])
            option.optional = True

    parsed = Args.parse("".split())
    assert parsed.foo is None


def test_override_add_argument() -> None:
    class BaseArgs:
        foo: str = option()

    @arcparser
    class Args(BaseArgs):
        bar: str

        @staticmethod
        def __post_init__(parser: Parser) -> None:
            parser.arguments["bar"] = Option("bar", name="bar")

    with pytest.raises(SystemExit):
        Args.parse("--foo foo".split())

    parsed = Args.parse("--foo foo --bar bar".split())
    assert parsed.foo == "foo" and parsed.bar == "bar"


def test_override_remove_argument() -> None:
    class BaseArgs:
        foo: str = option()

    @arcparser
    class Args(BaseArgs):
        @staticmethod
        def __post_init__(parser: Parser) -> None:
            del parser.arguments["foo"]

    with pytest.raises(SystemExit):
        Args.parse("--foo foo".split())

    parsed = Args.parse("".split())
    assert not hasattr(parsed, "foo")
