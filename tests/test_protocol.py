from dataclasses import dataclass
from typing import Protocol, Self

import pytest

from arcparse import ArcParser
from arcparse.arguments import option


class FooLike(Protocol):
    foo: str


class FooBarLike(FooLike, Protocol):
    bar: str


@dataclass
class FooBar(FooBarLike):
    foo: str
    bar: str

    @classmethod
    def from_foo(cls, string: str) -> Self:
        return cls(foo=string, bar="")

    @classmethod
    def from_foo_bar(cls, string: str) -> Self:
        return cls(*string.split(","))


def test_protocol_no_converter_invalid():
    class Args(ArcParser):
        foo: FooLike

    with pytest.raises(Exception):
        Args.parse("--foo foo".split())


def test_inh_protocol_no_converter_invalid():
    class Args(ArcParser):
        foo_bar: FooBarLike

    with pytest.raises(Exception):
        Args.parse("--foo foo".split())


def test_protocol_with_converter_valid():
    class Args(ArcParser):
        foo: FooLike = option(converter=FooBar.from_foo)

    args = Args.parse("--foo foo".split())
    assert args.foo.foo == "foo"


def test_inh_protocol_with_converter_valid():
    class Args(ArcParser):
        foo_bar: FooBarLike = option(converter=FooBar.from_foo_bar)

    args = Args.parse("--foo-bar foo,bar".split())
    assert args.foo_bar.foo == "foo"
    assert args.foo_bar.bar == "bar"


def test_protocol_dynamic_defaults_valid():
    class Args(ArcParser):
        foo: FooLike = option(converter=FooBar.from_foo)

    args = Args.parse([], defaults={"foo": "foo"})
    assert args.foo.foo == "foo"
