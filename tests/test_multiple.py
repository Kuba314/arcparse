import pytest

from arcparse import arcparser, option, positional
from arcparse.errors import InvalidArgument


@pytest.mark.parametrize(
    "string,result",
    [
        ("", []),
        ("--values", []),
        ("--values 1 2 3", [1, 2, 3]),
    ],
)
def test_opt_nargs(string: str, result: list[int]) -> None:
    @arcparser
    class Args:
        values: list[int]

    args = Args.parse(string.split())
    assert args.values == result


@pytest.mark.parametrize(
    "string,result",
    [
        ("", []),
        ("1 2 3", [1, 2, 3]),
    ],
)
def test_pos_nargs(string: str, result: list[int]) -> None:
    @arcparser
    class Args:
        values: list[int] = positional()

    args = Args.parse(string.split())
    assert args.values == result


@pytest.mark.parametrize(
    "string,result",
    [
        ("", None),
        ("--values", None),
        ("--values 1", [1]),
        ("--values 1 2", [1, 2]),
    ],
)
def test_opt_nargs_plus(string: str, result: list[int] | None) -> None:
    @arcparser
    class Args:
        values: list[int] = option(at_least_one=True)

    if result is None:
        with pytest.raises(SystemExit):
            Args.parse(string.split())
    else:
        args = Args.parse(string.split())
        assert args.values == result


@pytest.mark.parametrize(
    "string,result",
    [
        ("", None),
        ("1", [1]),
        ("1 2", [1, 2]),
    ],
)
def test_pos_nargs_plus(string: str, result: list[int] | None) -> None:
    @arcparser
    class Args:
        values: list[int] = positional(at_least_one=True)

    if result is None:
        with pytest.raises(SystemExit):
            Args.parse(string.split())
    else:
        args = Args.parse(string.split())
        assert args.values == result


@pytest.mark.parametrize(
    "string,result",
    [
        ("", []),
        ("-v 1 -v 2 -v 3", [1, 2, 3]),
        ("--value 1 --value 2 --value 3", [1, 2, 3]),
    ],
)
def test_opt_append(string: str, result: list[int]) -> None:
    @arcparser
    class Args:
        values: list[int] = option("-v", append=True, name_override="value")

    args = Args.parse(string.split())
    assert args.values == result


def test_multiple_invalid() -> None:
    with pytest.raises(InvalidArgument):
        option(append=True, at_least_one=True)
