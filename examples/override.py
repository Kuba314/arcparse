from typing import cast

from arcparse import Parser, arcparser
from arcparse.arguments import Option


class BaseArgs:
    foo: str
    bar: int


@arcparser
class Args(BaseArgs):
    @staticmethod
    def __post_init__(parser: Parser) -> None:
        # set "foo" argument's default to "foo"
        cast(Option, parser.arguments["foo"]).default = "foo"

        # delete "bar" argument
        del parser.arguments["bar"]

        # create new argument
        parser.arguments["baz"] = Option("baz", name="baz", default="baz")


if __name__ == "__main__":
    print(vars(Args.parse()))
