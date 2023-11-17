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

@pytest.mark.parametrize("parser", [Invalid1, Invalid2, Invalid3, Invalid4, Invalid5])
def test_invalid(parser: ArcParser) -> None:
    with pytest.raises(Exception):
        parser.parse([])
