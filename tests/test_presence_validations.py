from typing import Any, Iterator

import pytest

from arcparse import Parser, arcparser, positional, subparsers
from arcparse.validations import Constraint, imply, require


@pytest.fixture(scope="session")
def args_cls() -> Parser:
    @arcparser
    class ConfigArgs:
        list: bool
        unset: bool
        key: str | None = positional()
        value: str | None = positional()

        @classmethod
        def __presence_validations__(cls) -> Iterator[Constraint]:
            yield imply(cls.list, disallowed=[cls.unset, cls.key, cls.value])
            yield imply(cls.unset, required=[cls.key], disallowed=[cls.value])
            yield require(cls.key, cls.value)

    return ConfigArgs


@pytest.fixture(scope="session")
def subparsers_args_cls() -> Parser:
    class FooBar:
        foo: bool
        bar: bool

        @classmethod
        def __presence_validations__(cls) -> Iterator[Constraint]:
            yield imply(cls.foo, required=[cls.bar])

    class BarFoo:
        bar: bool
        foo: bool

        @classmethod
        def __presence_validations__(cls) -> Iterator[Constraint]:
            yield imply(cls.bar, required=[cls.foo])

    @arcparser
    class Args:
        arg: FooBar | BarFoo = subparsers("foobar", "barfoo")

    return Args


@pytest.mark.parametrize(
    "string,result",
    [
        ("--list", {"list": True}),
        ("--unset foo", {"unset": True, "key": "foo"}),
        ("foo bar", {"key": "foo", "value": "bar"}),
        ("--list --unset", Exception),
        ("--list foo", Exception),
        ("--unset foo bar", Exception),
        ("foo bar baz", SystemExit),
    ],
)
def test_validation(args_cls: Parser, string: str, result: dict[str, Any] | type[BaseException]) -> None:
    if isinstance(result, type) and issubclass(result, BaseException):
        with pytest.raises(result):
            args_cls.parse(string.split())
    else:
        args = args_cls.parse(string.split())
        for k, v in result.items():
            assert getattr(args, k) == v


@pytest.mark.parametrize(
    "string,result",
    [
        ("foobar", {"foo": False, "bar": False}),
        ("barfoo", {"foo": False, "bar": False}),
        ("foobar --foo --bar", {"foo": True, "bar": True}),
        ("barfoo --bar --foo", {"bar": True, "foo": True}),
        ("foobar --bar", {"foo": False, "bar": True}),
        ("barfoo --foo", {"bar": False, "foo": True}),
        ("", SystemExit),
        ("foobar --foo", Exception),
        ("barfoo --bar", Exception),
    ],
)
def test_validation_subparsers(
    subparsers_args_cls: Parser, string: str, result: dict[str, Any] | type[BaseException]
) -> None:
    if isinstance(result, type) and issubclass(result, BaseException):
        with pytest.raises(result):
            subparsers_args_cls.parse(string.split())
    else:
        args = subparsers_args_cls.parse(string.split())
        for k, v in result.items():
            assert getattr(args.arg, k) == v
