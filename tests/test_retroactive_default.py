from arcparse import arcparser, option, positional
from arcparse.arguments import BaseValueArgument


def test_retroactive_default_option_implicit() -> None:
    @arcparser
    class Args:
        foo: str

    for _, argument in Args.all_arguments:
        if isinstance(argument, BaseValueArgument):
            argument.default = "foo"

    parsed = Args.parse("".split())
    assert parsed.foo == "foo"

    parsed = Args.parse("--foo bar".split())
    assert parsed.foo == "bar"


def test_retroactive_default_option_explicit() -> None:
    @arcparser
    class Args:
        foo: str = option()

    for _, argument in Args.all_arguments:
        if isinstance(argument, BaseValueArgument):
            argument.default = "foo"

    parsed = Args.parse("".split())
    assert parsed.foo == "foo"

    parsed = Args.parse("--foo bar".split())
    assert parsed.foo == "bar"


def test_retroactive_default_positional() -> None:
    @arcparser
    class Args:
        foo: str = positional()

    for _, argument in Args.all_arguments:
        if isinstance(argument, BaseValueArgument):
            argument.default = "foo"

    parsed = Args.parse("".split())
    assert parsed.foo == "foo"

    parsed = Args.parse("bar".split())
    assert parsed.foo == "bar"
