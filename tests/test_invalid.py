import pytest

from arcparse import ArcParser, positional


class Invalid1(ArcParser):
    x: bool | None

class Invalid2(ArcParser):
    x: bool = positional()

class Invalid3(ArcParser):
    x: int | str

class Invalid4(ArcParser):
    x: int | str | None

class Invalid5(ArcParser):
    x = positional()

class Invalid6(ArcParser):
    x: bool = True

class Invalid7(ArcParser):
    x: bool = False

@pytest.mark.parametrize("parser", [Invalid1, Invalid2, Invalid3, Invalid4, Invalid5, Invalid6, Invalid7])
def test_invalid(parser: ArcParser) -> None:
    with pytest.raises(Exception):
        parser.parse([])



def test_untyped_variable() -> None:
    class Args(ArcParser):
        foo = 1

    with pytest.raises(SystemExit):
        Args.parse(["--foo", "2"])
