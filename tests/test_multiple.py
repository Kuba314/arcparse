import pytest

from arcparse import arcparser, option, positional


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
    ],
)
def test_opt_append(string: str, result: list[int]) -> None:
    @arcparser
    class Args:
        values: list[int] = option("-v", append=True, name_override="value")

    args = Args.parse(string.split())
    assert args.values == result


def test_append_default() -> None:
    @arcparser
    class Args:
        values: list[int] = option("-v", append=True, default=[1, 2, 3])

    args = Args.parse([])
    assert args.values == [1, 2, 3]

    args = Args.parse("-v 4 -v 5".split())
    assert args.values == [4, 5]


def test_append_at_least_one() -> None:
    @arcparser
    class Args:
        values: list[int] = option("-v", append=True, at_least_one=True)

    with pytest.raises(SystemExit):
        Args.parse()

    args = Args.parse("-v 4 -v 5".split())
    assert args.values == [4, 5]
