from enum import StrEnum, auto
from typing import Literal
import re

from arcparse import arcparser, dict_option, itemwise, option


class Color(StrEnum):
    RED = auto()
    GREEN = auto()


def parse_result(arg: str) -> bool:
    if arg == "pass":
        return True
    return False


@arcparser
class Args:
    value: int

    # automatically populates choices
    consent: Literal["yes", "no"]

    # also automatically populates choices
    color: Color

    # also automatically populates choices
    mode: int = dict_option({"auto": 0, "manual": 1})

    # compiles to a regex using re.compile
    regex: re.Pattern

    result: bool = option(converter=parse_result)

    # argument accepts multiple command-line values if no converter is set, or itemwise is used
    # the names field will contain multiple values from a single argument
    names: list[str] = option(converter=lambda x: x.split())

    # the results field will contain multiple values, each from a separate argument
    results: list[bool] = option(converter=itemwise(parse_result))


if __name__ == "main":
    print(vars(Args.parse()))
