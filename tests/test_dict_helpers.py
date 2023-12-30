import pytest

from arcparse import arcparser, dict_option, dict_positional
from arcparse.errors import InvalidArgument


dict_ = {
    "foo": 1,
    "bar": 0,
}


def test_dict_positional_default_in_dict() -> None:
    with pytest.raises(InvalidArgument):
        dict_positional(dict_, default=2)


@pytest.mark.parametrize(
    "arg_string,value",
    [
        ("foo", 1),
        ("bar", 0),
    ]
)
def test_dict_positional(arg_string: str, value: int) -> None:
    @arcparser
    class Args:
        foo_bar: int = dict_positional(dict_)

    parsed = Args.parse(arg_string.split())
    assert parsed.foo_bar == value


def test_dict_option_default_in_dict() -> None:
    with pytest.raises(InvalidArgument):
        dict_option(dict_, default=2)


@pytest.mark.parametrize(
    "arg_string,value",
    [
        ("--foo-bar foo", 1),
        ("--foo-bar bar", 0),
    ]
)
def test_dict_option(arg_string: str, value: int) -> None:
    @arcparser
    class Args:
        foo_bar: int = dict_option(dict_)

    parsed = Args.parse(arg_string.split())
    assert parsed.foo_bar == value
