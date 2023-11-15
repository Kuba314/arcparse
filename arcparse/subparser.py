from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import dataclass
from types import NoneType
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import ArcParser


@dataclass
class _Subparsers:
    names: list[str]

    def apply(
        self,
        parser: ArgumentParser,
        name: str,
        subparser_types: Sequence[type["ArcParser"] | None],
        defaults: dict[str, Any] = {},
    ) -> None:
        subparsers_kwargs: dict = {"dest": name}
        if NoneType not in subparser_types:
            subparsers_kwargs["required"] = True
        subparsers = parser.add_subparsers(**subparsers_kwargs)

        nonnull_subparser_types: list[type["ArcParser"]] = [
            typ for typ in subparser_types if typ is not NoneType
        ]  # type: ignore  (NoneType is getting confused with None)

        for name, subparser_type in zip(self.names, nonnull_subparser_types):
            subparser = subparsers.add_parser(name)
            subparser_type._apply(subparser, defaults.get("name", {}))


def subparsers(*args: str) -> Any:
    return _Subparsers(names=list(args))
