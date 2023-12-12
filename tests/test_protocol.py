from dataclasses import dataclass
from typing import Protocol, Self

import pytest

from arcparse import arcparser, option


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
    class Args:
        foo: FooLike

    with pytest.raises(Exception):
        arcparser(Args)


def test_inh_protocol_no_converter_invalid():
    class Args:
        foo_bar: FooBarLike

    with pytest.raises(Exception):
        arcparser(Args)


def test_protocol_with_converter_valid():
    @arcparser
    class Args:
        foo: FooLike = option(converter=FooBar.from_foo)

    args = Args.parse("--foo foo".split())
    assert args.foo.foo == "foo"


def test_inh_protocol_with_converter_valid():
    @arcparser
    class Args:
        foo_bar: FooBarLike = option(converter=FooBar.from_foo_bar)

    args = Args.parse("--foo-bar foo,bar".split())
    assert args.foo_bar.foo == "foo"
    assert args.foo_bar.bar == "bar"
