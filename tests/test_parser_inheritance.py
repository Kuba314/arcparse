from arcparse import arcparser


@arcparser
class BaseArgs:
    foo: str | None


@arcparser(BaseArgs)
class Args:
    bar: str | None


def test_parser_inheritance() -> None:
    parsed = Args.parse("".split())
    parsed.foo is None
    parsed.bar is None

    parsed = Args.parse("--foo foo".split())
    parsed.foo == "foo"
    parsed.bar is None

    parsed = Args.parse("--bar bar".split())
    parsed.foo is None
    parsed.bar == "bar"

    parsed = Args.parse("--foo foo --bar bar".split())
    parsed.foo == "foo"
    parsed.bar == "bar"
