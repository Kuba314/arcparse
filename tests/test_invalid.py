import pytest

from arcparse import arcparser, positional
from arcparse.errors import InvalidArgument, InvalidTypehint, MissingConverter


def test_no_bool_inner_type_without_converter() -> None:
    class Args:
        x: bool | None

    with pytest.raises(MissingConverter):
        arcparser(Args)


def test_no_bool_valued_type_without_converter() -> None:
    class Args:
        x: bool = positional()

    with pytest.raises(InvalidTypehint):
        arcparser(Args)


def test_no_nonnone_union() -> None:
    class Args:
        x: int | str

    with pytest.raises(InvalidTypehint):
        arcparser(Args)


def test_no_large_union_typehint() -> None:
    class Args:
        x: int | str | None

    with pytest.raises(InvalidTypehint):
        arcparser(Args)


def test_no_typehint_invalid() -> None:
    class Args:
        x = positional()

    with pytest.raises(InvalidTypehint):
        arcparser(Args)


def test_no_default_for_flag() -> None:
    class ArgsTrue:
        x: bool = True

    class ArgsFalse:
        x: bool = False

    with pytest.raises(InvalidArgument):
        arcparser(ArgsTrue)

    with pytest.raises(InvalidArgument):
        arcparser(ArgsFalse)


def test_untyped_nonargument_variable_valid() -> None:
    @arcparser
    class Args:
        foo = 1

    with pytest.raises(SystemExit):
        Args.parse(["--foo", "2"])
