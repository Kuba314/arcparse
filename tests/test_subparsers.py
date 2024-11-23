from types import NoneType
from typing import Any, Protocol

import pytest

from arcparse import arcparser, flag, positional, subparsers
from arcparse.errors import InvalidParser


class FooArgs:
    arg1: str


class BarArgs:
    arg2: int = positional()


@arcparser
class ReqArgs:
    action: FooArgs | BarArgs = subparsers("foo", "bar")


@arcparser
class OptArgs:
    action: FooArgs | BarArgs | None = subparsers("foo", "bar")


@pytest.mark.parametrize(
    "string,result",
    [
        ("", SystemExit),
        ("foo --arg1 foo", (FooArgs, {"arg1": "foo"})),
        ("bar 123", (BarArgs, {"arg2": 123})),
        ("bar bar", ValueError),
    ],
)
def test_subparsers_required(string: str, result: tuple[type, dict[str, Any]] | type[BaseException]) -> None:
    if isinstance(result, type):
        with pytest.raises(result):
            ReqArgs.parse(string.split())
    else:
        args = ReqArgs.parse(string.split())
        type_, value_dict = result
        assert isinstance(action := args.action, type_)
        for k, v in value_dict.items():
            assert getattr(action, k) == v


@pytest.mark.parametrize(
    "string,result",
    [
        ("", (NoneType, None)),
        ("foo --arg1 foo", (FooArgs, {"arg1": "foo"})),
        ("bar 123", (BarArgs, {"arg2": 123})),
        ("bar bar", ValueError),
    ],
)
def test_subparsers_optional(string: str, result: tuple[type, dict[str, Any] | None] | type[BaseException]) -> None:
    if isinstance(result, type):
        with pytest.raises(result):
            OptArgs.parse(string.split())
    else:
        args = OptArgs.parse(string.split())
        type_, value_dict = result
        assert isinstance(action := args.action, type_)
        if value_dict is None:
            assert action is None
        else:
            for k, v in value_dict.items():
                assert getattr(action, k) == v


def test_only_one_subparsers() -> None:
    class Foo:
        foo: str

    class Bar:
        bar: str

    class Baz:
        baz: str

    class Boo:
        boo: str

    class Args:
        foo_or_bar: Foo | Bar = subparsers("foo", "bar")
        baz_or_boo: Baz | Boo = subparsers("baz", "boo")

    with pytest.raises(InvalidParser):
        arcparser(Args)


def test_nested_subparsers() -> None:
    class Bar:
        bar: bool

    class Baz:
        baz: bool

    class BarBaz:
        bar_or_baz: Bar | Baz = subparsers("bar", "baz")

    class Boo:
        boo: bool

    @arcparser
    class Args:
        barbaz_or_boo: BarBaz | Boo = subparsers("barbaz", "boo")

    parsed = Args.parse("barbaz bar --bar".split())
    assert isinstance(barbaz := parsed.barbaz_or_boo, BarBaz) and isinstance(bar := barbaz.bar_or_baz, Bar) and bar.bar

    parsed = Args.parse("barbaz baz --baz".split())
    assert isinstance(barbaz := parsed.barbaz_or_boo, BarBaz) and isinstance(baz := barbaz.bar_or_baz, Baz) and baz.baz

    parsed = Args.parse("boo --boo".split())
    assert isinstance(boo := parsed.barbaz_or_boo, Boo) and boo.boo


def test_subparser_actions() -> None:
    class AddAction:
        name: str

        def act(self) -> str:
            return self.name

    class ListAction:
        all: bool = flag("-a", help="list all")

        def act(self) -> str:
            return str(self.all)

    @arcparser
    class Args:
        action: AddAction | ListAction = subparsers("add", "list")

    parsed = Args.parse("add --name foo".split())
    assert parsed.action.act() == "foo"

    parsed = Args.parse("list".split())
    assert parsed.action.act() == "False"

    parsed = Args.parse("list -a".split())
    assert parsed.action.act() == "True"


def test_subparsers_interface() -> None:
    class Action(Protocol):
        def act(self) -> str: ...

    class AddAction:
        name: str

        def act(self) -> str:
            return self.name

    class ListAction:
        all: bool = flag("-a", help="list all")

        def act(self) -> str:
            return str(self.all)

    @arcparser
    class Args:
        action: Action = subparsers(
            add=AddAction,
            list=ListAction,
        )

    parsed = Args.parse("add --name foo".split())
    assert parsed.action.act() == "foo"

    parsed = Args.parse("list".split())
    assert parsed.action.act() == "False"

    parsed = Args.parse("list -a".split())
    assert parsed.action.act() == "True"


def test_subparsers_interface_optional() -> None:
    class Action(Protocol):
        def act(self) -> str: ...

    class AddAction:
        name: str

        def act(self) -> str:
            return self.name

    class ListAction:
        all: bool = flag("-a", help="list all")

        def act(self) -> str:
            return str(self.all)

    @arcparser
    class Args:
        action: Action | None = subparsers(
            add=AddAction,
            list=ListAction,
        )

    parsed = Args.parse("".split())
    assert parsed.action is None

    parsed = Args.parse("add --name foo".split())
    assert parsed.action is not None and parsed.action.act() == "foo"

    parsed = Args.parse("list".split())
    assert parsed.action is not None and parsed.action.act() == "False"

    parsed = Args.parse("list -a".split())
    assert parsed.action is not None and parsed.action.act() == "True"
