import pytest

from arcparse import arcparser, option, positional
from arcparse.errors import InvalidArgument


def test_name_override() -> None:
    @arcparser
    class ArgsOption:
        foo: str = option(name_override="bar")

    parsed = ArgsOption.parse("--bar bar".split())
    assert parsed.foo == "bar"

    @arcparser
    class ArgsPositional:
        foo: str = positional(name_override="bar")

    parsed = ArgsPositional.parse("bar".split())
    assert parsed.foo == "bar"

    with pytest.raises(InvalidArgument):
        option(short_only=True, name_override="foo")
