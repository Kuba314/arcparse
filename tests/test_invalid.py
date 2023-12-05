import pytest

from arcparse import arcparser, positional


class Invalid1:
    x: bool | None

class Invalid2:
    x: bool = positional()

class Invalid3:
    x: int | str

class Invalid4:
    x: int | str | None

class Invalid5:
    x = positional()

class Invalid6:
    x: bool = True

class Invalid7:
    x: bool = False

@pytest.mark.parametrize("args_shape", [Invalid1, Invalid2, Invalid3, Invalid4, Invalid5, Invalid6, Invalid7])
def test_invalid(args_shape: type) -> None:
    with pytest.raises(Exception):
        arcparser(args_shape)


def test_untyped_variable() -> None:
    @arcparser
    class Args:
        foo = 1

    with pytest.raises(SystemExit):
        Args.parse(["--foo", "2"])
