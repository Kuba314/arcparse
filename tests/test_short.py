import pytest

from arcparse import arcparser, flag, option
from arcparse.errors import InvalidArgument


def test_short_option_invalid() -> None:
    with pytest.raises(InvalidArgument):
        option("-fo")

    with pytest.raises(InvalidArgument):
        @arcparser
        class Args:
            foo: str = option(short_only=True)


def test_short_flag_invalid() -> None:
    with pytest.raises(InvalidArgument):
        flag("-fo")

    with pytest.raises(InvalidArgument):
        @arcparser
        class Args:
            foo: bool = flag(short_only=True)
